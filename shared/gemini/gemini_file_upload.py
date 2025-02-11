"""Module for file uploads and content generation with Gemini API."""

import os
from typing import Union, BinaryIO, Optional
import mimetypes
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from .utils import async_retry_with_backoff, logger


class GeminiFileUpload:
    def __init__(self):
        """Initialize the Gemini file upload and content generation module."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        self._logger = logger.getChild("file_upload")

    @async_retry_with_backoff()
    async def process_file(
        self,
        file_path: Union[str, BinaryIO],
        prompt: str,
        mime_type: Optional[str] = None,
    ) -> GenerateContentResponse:
        """Upload a file and generate content based on it using retry mechanism.

        Args:
            file_path: Path to file or file-like object
            prompt: Text prompt to guide the content generation
            mime_type: Optional MIME type of the file. If not provided, will be guessed

        Returns:
            GenerateContentResponse: The response from Gemini API

        Raises:
            ValueError: If file upload fails
            RuntimeError: If API call fails after retries
        """
        try:
            # Validate file first
            self.validate_file(file_path, mime_type)
            self._logger.info("File validation successful")

            # Handle file path or file-like object
            if isinstance(file_path, str):
                self._logger.info(f"Reading file from path: {file_path}")
                with open(file_path, "rb") as f:
                    file_content = f.read()
                if not mime_type:
                    mime_type = mimetypes.guess_type(file_path)[0]
                    self._logger.info(f"Detected MIME type: {mime_type}")
            else:
                self._logger.info("Reading from file-like object")
                file_content = file_path.read()
                if not mime_type:
                    raise ValueError("mime_type must be provided for file-like objects")

            # Upload file to Gemini
            file_parts = [{"data": file_content, "mime_type": mime_type}]

            # Generate content using the uploaded file
            self._logger.info(f"Processing file with prompt: {prompt[:50]}...")
            response = await self.model.generate_content_async([prompt, *file_parts])
            self._logger.info("Successfully received response from API")
            return response

        except ValueError as e:
            self._logger.error(f"File validation failed: {str(e)}")
            raise
        except Exception as e:
            self._logger.error(f"Failed to process file: {str(e)}")
            raise RuntimeError(f"Failed to process file: {str(e)}")

    @staticmethod
    def validate_file(
        file_path: Union[str, BinaryIO], mime_type: Optional[str] = None
    ) -> bool:
        """Validate that a file can be processed.

        Args:
            file_path: Path to file or file-like object
            mime_type: Optional MIME type of the file

        Returns:
            bool: True if file is valid

        Raises:
            ValueError: If file is invalid
        """
        try:
            if isinstance(file_path, str):
                if not os.path.exists(file_path):
                    raise ValueError(f"File not found: {file_path}")
                if not mime_type:
                    mime_type = mimetypes.guess_type(file_path)[0]
                    if not mime_type:
                        raise ValueError("Could not determine file type")
            elif not hasattr(file_path, "read"):
                raise ValueError("Invalid file object")
            elif not mime_type:
                raise ValueError("mime_type must be provided for file-like objects")
            return True
        except Exception as e:
            raise ValueError(f"Invalid file: {str(e)}")
