import logging
import os
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Scraper Service",
    description="Service for scraping and processing web content",
    version="1.0.0"
)

# Vector DB URL for storing embeddings
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://vector_db:8005")

class ScrapingRequest(BaseModel):
    url: HttpUrl
    max_depth: int = 1
    max_pages: int = 10
    selectors: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None

class ScrapingResponse(BaseModel):
    content: Dict[str, str]  # URL to content mapping
    metadata: Dict
    discovered_urls: List[str]

async def is_valid_url(url: str, base_domain: str) -> bool:
    """Check if URL is valid and belongs to the same domain."""
    try:
        parsed = urlparse(url)
        return parsed.netloc == base_domain and parsed.scheme in ['http', 'https']
    except Exception:
        return False

async def extract_text_content(html: str, selectors: Optional[List[str]] = None) -> str:
    """Extract text content from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for element in soup(['script', 'style']):
        element.decompose()
    
    if selectors:
        content = []
        for selector in selectors:
            elements = soup.select(selector)
            content.extend(element.get_text(strip=True) for element in elements)
        return "\n".join(content)
    
    return soup.get_text(separator="\n", strip=True)

async def store_in_vector_db(url: str, content: str) -> bool:
    """Store the scraped content in the vector database."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VECTOR_DB_URL}/vectors/add",
                json={
                    "text": content,
                    "metadata": {"url": url, "type": "webpage"}
                },
                timeout=10.0
            )
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Error storing in vector DB: {str(e)}")
        return False

async def scrape_url(url: str, selectors: Optional[List[str]] = None) -> tuple[str, Set[str]]:
    """Scrape content and extract links from a URL using Playwright."""
    discovered_urls = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle")
            html_content = await page.content()
            
            # Extract links
            links = await page.eval_on_selector_all('a[href]', """
                elements => elements.map(el => el.href)
            """)
            discovered_urls.update(links)
            
            # Extract content
            content = await extract_text_content(html_content, selectors)
            
            await browser.close()
            return content, discovered_urls
            
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            await browser.close()
            raise HTTPException(status_code=500, detail=f"Error scraping URL: {str(e)}")

@app.post("/scrape", response_model=ScrapingResponse)
async def scrape_website(request: ScrapingRequest):
    """Scrape website content with specified depth and store in vector DB."""
    try:
        base_domain = urlparse(str(request.url)).netloc
        to_visit = {str(request.url)}
        visited = set()
        content_map = {}
        all_discovered_urls = set()
        
        while to_visit and len(visited) < request.max_pages:
            current_url = to_visit.pop()
            if current_url in visited:
                continue
                
            logger.info(f"Scraping URL: {current_url}")
            content, discovered_urls = await scrape_url(current_url, request.selectors)
            
            # Store content
            content_map[current_url] = content
            visited.add(current_url)
            all_discovered_urls.update(discovered_urls)
            
            # Store in vector DB
            await store_in_vector_db(current_url, content)
            
            # Add new URLs to visit if within depth
            if len(visited) < request.max_depth:
                for url in discovered_urls:
                    if (await is_valid_url(url, base_domain) and 
                        url not in visited and 
                        not any(pattern in url for pattern in (request.exclude_patterns or []))):
                        to_visit.add(url)
            
            # Small delay to be nice to the server
            await asyncio.sleep(1)
        
        return ScrapingResponse(
            content=content_map,
            metadata={
                "pages_scraped": len(visited),
                "total_discovered_urls": len(all_discovered_urls)
            },
            discovered_urls=list(all_discovered_urls)
        )
        
    except Exception as e:
        logger.error(f"Error in scrape_website: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check the health of the service and its dependencies."""
    dependencies = {
        "vector_db": "unhealthy",
        "playwright": "unhealthy"
    }
    
    try:
        # Check Vector DB connection
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{VECTOR_DB_URL}/health")
            if response.status_code == 200:
                dependencies["vector_db"] = "healthy"
    except Exception as e:
        logger.error(f"Vector DB health check failed: {str(e)}")
    
    try:
        # Check Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            await browser.close()
            dependencies["playwright"] = "healthy"
    except Exception as e:
        logger.error(f"Playwright health check failed: {str(e)}")
    
    # Overall status is healthy only if all dependencies are healthy
    overall_status = "healthy" if all(status == "healthy" for status in dependencies.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "rag_scraper",
        "dependencies": dependencies
    } 