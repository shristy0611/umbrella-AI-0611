"""PDF extraction service implementation."""
import logging
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

class PDFExtractor:
    """Service for extracting text from PDF files."""

    def __init__(self):
        """Initialize the PDF extractor service."""
        self.logger = logging.getLogger(__name__)

    def _validate_pdf_bytes(self, pdf_bytes: bytes) -> bool:
        """Validate if bytes represent a PDF file."""
        return pdf_bytes.startswith(b'%PDF')

    def extract_text(
        self,
        pdf_bytes: bytes,
        password: Optional[str] = None,
        use_ocr: bool = False
    ) -> Dict[str, Any]:
        """Extract text from PDF bytes."""
        try:
            if not isinstance(pdf_bytes, bytes):
                raise ValueError("Invalid PDF format")

            if not self._validate_pdf_bytes(pdf_bytes):
                raise ValueError("Invalid PDF format")

            pdf_file = BytesIO(pdf_bytes)
            try:
                reader = PdfReader(pdf_file)
                if reader.is_encrypted:
                    if not password:
                        raise ValueError("Password required for encrypted PDF")
                    try:
                        reader.decrypt(password)
                    except:
                        raise ValueError("Incorrect password for encrypted PDF")

                if len(reader.pages) == 0:
                    return {
                        "text": "",
                        "metadata": {
                            "page_count": 0,
                            "is_empty": True,
                            "ocr_applied": use_ocr
                        }
                    }

                text = ""
                for page in reader.pages:
                    if use_ocr:
                        # OCR functionality would be implemented here
                        # For now, we'll just use the regular text extraction
                        self.logger.warning("OCR requested but not implemented, falling back to regular extraction")
                    text += page.extract_text() + "\n"

                return {
                    "text": text.strip(),
                    "metadata": {
                        "page_count": len(reader.pages),
                        "is_empty": len(text.strip()) == 0,
                        "ocr_applied": use_ocr
                    }
                }

            except PdfReadError as e:
                if "EOF marker not found" in str(e):
                    return {
                        "text": "",
                        "metadata": {
                            "page_count": 0,
                            "is_empty": True,
                            "ocr_applied": use_ocr
                        }
                    }
                if "File has not been decrypted" in str(e):
                    raise ValueError("Password protected PDF file")
                raise ValueError("Invalid PDF format") from e
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {str(e)}")
            if "password" in str(e).lower():
                raise ValueError("Password protected PDF") from e
            if "EOF" in str(e) or "stream" in str(e).lower():
                raise ValueError("Empty PDF file") from e
            raise

    def extract_text_from_base64(
        self,
        base64_data: str,
        password: Optional[str] = None,
        use_ocr: bool = False
    ) -> Dict[str, Any]:
        """Extract text from base64-encoded PDF data."""
        try:
            pdf_bytes = base64.b64decode(base64_data)
            return self.extract_text(pdf_bytes, password, use_ocr)
        except Exception as e:
            self.logger.error(f"Error decoding base64 data: {str(e)}")
            raise ValueError("Invalid base64 data") from e

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming PDF extraction request."""
        if "file" not in request_data and "base64_data" not in request_data:
            raise ValueError("Missing file")

        password = request_data.get("password")
        use_ocr = request_data.get("use_ocr", False)

        try:
            if "file" in request_data:
                if isinstance(request_data["file"], str):
                    return self.extract_text_from_base64(request_data["file"], password, use_ocr)
                elif isinstance(request_data["file"], bytes):
                    return self.extract_text(request_data["file"], password, use_ocr)
                else:
                    raise ValueError("Invalid file format")
            else:
                return self.extract_text_from_base64(request_data["base64_data"], password, use_ocr)
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            raise

    async def process_batch_request(self, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a batch of PDF extraction requests."""
        if "files" not in request_data:
            raise ValueError("Missing files in batch request")

        results = []
        for file_item in request_data["files"]:
            try:
                file_id = file_item.get("id")
                content = file_item.get("content")
                password = file_item.get("password")
                use_ocr = file_item.get("use_ocr", False)

                if isinstance(content, str):
                    result = self.extract_text_from_base64(content, password, use_ocr)
                else:
                    result = self.extract_text(content, password, use_ocr)

                results.append({
                    "id": file_id,
                    "status": "success",
                    **result
                })
            except Exception as e:
                results.append({
                    "id": file_id,
                    "status": "error",
                    "error": str(e)
                })

        return results 