from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
import httpx
from bs4 import BeautifulSoup
import re

app = FastAPI(title="RAG Scraper Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    url: HttpUrl
    max_depth: int = 1
    max_pages: int = 10
    selectors: Optional[List[str]] = ["p", "h1", "h2", "h3", "article"]
    exclude_patterns: Optional[List[str]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "scraper",
        "dependencies": {}
    }

@app.post("/scrape")
async def scrape_website(request: ScrapeRequest):
    """Scrape content from a website."""
    try:
        async with httpx.AsyncClient() as client:
            # Fetch the main page
            response = await client.get(str(request.url))
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content based on selectors
            content = {}
            for selector in request.selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text:
                        content[str(request.url)] = content.get(str(request.url), "") + text + "\n"
            
            # Find links for potential deeper crawling
            discovered_urls = []
            if request.max_depth > 0:
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    if url.startswith('http'):
                        discovered_urls.append(url)
            
            return {
                "content": content,
                "metadata": {
                    "pages_scraped": 1,
                    "total_discovered_urls": len(discovered_urls)
                },
                "discovered_urls": discovered_urls[:10]  # Limit to 10 URLs
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004) 