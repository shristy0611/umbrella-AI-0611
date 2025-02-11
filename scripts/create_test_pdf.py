from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

def create_sample_pdf(output_path):
    """Create a sample PDF file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create the PDF
    c = canvas.Canvas(output_path, pagesize=letter)
    
    # Add some text
    c.drawString(100, 750, "UMBRELLA-AI Test Document")
    c.drawString(100, 700, "This is a sample PDF document for testing the PDF extraction service.")
    c.drawString(100, 650, "The service should be able to extract and process this text.")
    
    # Add a table
    c.drawString(100, 550, "Sample Table:")
    data = [
        ["ID", "Name", "Value"],
        ["1", "Item A", "100"],
        ["2", "Item B", "200"],
        ["3", "Item C", "300"]
    ]
    
    y = 500
    for row in data:
        x = 100
        for item in row:
            c.drawString(x, y, item)
            x += 100
        y -= 20
    
    # Save the PDF
    c.save()

if __name__ == "__main__":
    create_sample_pdf("test_data/sample.pdf") 