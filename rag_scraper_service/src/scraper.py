"""Service for scraping web content for RAG."""

import logging
from typing import Dict, List, Optional, Set, Any
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from aiohttp.client_exceptions import ClientError, ServerTimeoutError
from aiohttp import ClientTimeout
import asyncio
import re

logger = logging.getLogger(__name__)

class RAGScraper:
    def __init__(self):
        """Initialize the RAG scraper service."""
        self.logger = logging.getLogger(__name__)
        self.visited_urls: Set[str] = set()
        self.default_selectors = ['p', 'h1', 'h2', 'h3', 'article']
        self.timeout = ClientTimeout(total=30)

    def _validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text.strip()

    def _extract_content(self, html: str, selectors: List[str]) -> str:
        """Extract content from HTML using specified selectors."""
        soup = BeautifulSoup(html, 'html.parser')
        content = []
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = self._clean_text(element.get_text())
                if text:
                    content.append(text)
        
        return "\n".join(content)

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            if self._validate_url(href):
                links.append(href)
        
        return links

    async def scrape_page(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Scrape a single page."""
        if not self._validate_url(url):
            raise ValueError("Invalid URL")

        selectors = selectors or self.default_selectors
        timeout_obj = ClientTimeout(total=timeout) if timeout else self.timeout

        try:
            async with aiohttp.ClientSession() as session:
                try:
                    response = await session.get(url, timeout=timeout_obj)
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}")
                    html = await response.text()
                except asyncio.TimeoutError:
                    logger.error("Timeout scraping %s", url)
                    raise TimeoutError(f"Request timed out for {url}")
                except aiohttp.ClientError as e:
                    logger.error("Error scraping %s: %s", url, str(e))
                    raise ValueError(f"Failed to fetch {url}: {str(e)}")

            content = self._extract_content(html, selectors)
            links = self._extract_links(html, url)

            return {
                "url": url,
                "content": content,
                "links": links
            }

        except Exception as e:
            logger.error("Error scraping %s: %s", url, str(e), exc_info=True)
            raise

    async def scrape_recursive(
        self,
        base_url: str,
        max_depth: int = 1,
        selectors: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        visited: Optional[set] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """Recursively scrape pages starting from base_url."""
        if visited is None:
            visited = set()
        if current_depth > max_depth:
            return []
        if base_url in visited:
            return []

        visited.add(base_url)
        results = []

        try:
            # Scrape current page
            result = await self.scrape_page(base_url, selectors, timeout)
            results.append(result)

            # Recursively scrape linked pages
            if current_depth < max_depth:
                tasks = []
                for link in result["links"]:
                    if link not in visited:
                        task = self.scrape_recursive(
                            link,
                            max_depth,
                            selectors,
                            timeout,
                            visited,
                            current_depth + 1
                        )
                        tasks.append(task)
                
                if tasks:
                    child_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for child_result in child_results:
                        if isinstance(child_result, list):
                            results.extend(child_result)

            return results

        except Exception as e:
            logger.error("Error in recursive scraping of %s: %s", base_url, str(e), exc_info=True)
            return results

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single scraping request."""
        if "url" not in request_data:
            raise ValueError("URL is required")

        url = request_data["url"]
        options = request_data.get("options", {})
        max_depth = options.get("max_depth", 0)
        selectors = options.get("selectors", None)

        if max_depth > 0:
            results = await self.scrape_recursive(url, max_depth=max_depth, selectors=selectors)
            content = []
            for result in results:
                if isinstance(result.get("content"), str):
                    content.append(result["content"])
                elif isinstance(result.get("content"), list):
                    content.extend(item["text"] for item in result["content"])
            
            return {
                "content": " ".join(content),
                "raw_results": results,
                "metadata": {
                    "max_depth": max_depth,
                    "pages_scraped": len(results)
                }
            }
        else:
            result = await self.scrape_page(url, selectors=selectors)
            return {
                "content": result["content"],
                "raw_content": result.get("raw_content", []),
                "metadata": result["metadata"]
            }

    async def process_batch_request(self, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process multiple scraping requests in parallel."""
        if "urls" not in request_data:
            raise ValueError("URLs list is required")

        urls = request_data["urls"]
        options = request_data.get("options", {})
        max_depth = options.get("max_depth", 0)
        selectors = options.get("selectors", None)
        timeout = options.get("timeout")

        results = []
        for url_data in urls:
            url_id = url_data.get("id")
            url = url_data.get("url")
            
            try:
                if not url:
                    raise ValueError("Missing URL")
                
                if max_depth > 0:
                    scraped_data = await self.scrape_recursive(
                        url,
                        max_depth=max_depth,
                        selectors=selectors,
                        timeout=timeout
                    )
                else:
                    scraped_data = await self.scrape_page(
                        url,
                        selectors=selectors,
                        timeout=timeout
                    )
                
                results.append({
                    "id": url_id,
                    "success": True,
                    "content": scraped_data
                })
                
            except Exception as e:
                logger.error("Error processing request for %s: %s", url_id, str(e))
                results.append({
                    "id": url_id,
                    "success": False,
                    "error": str(e)
                })

        return results 