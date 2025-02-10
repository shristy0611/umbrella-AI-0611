from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2
import io
import os

app = FastAPI(title="PDF Extraction Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "pdf-extraction",
        "dependencies": {}
    }

@app.post("/extract")
async def extract_text(file: UploadFile):
    """Extract text from a PDF file."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read the uploaded file into memory
        content = await file.read()
        pdf_file = io.BytesIO(content)
        
        # Extract text using PyPDF2
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return {
            "text": text,
            "pages": len(reader.pages),
            "metadata": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 