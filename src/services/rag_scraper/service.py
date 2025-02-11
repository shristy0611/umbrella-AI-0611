"""RAG scraper service implementation."""

import logging
from typing import Dict, Any, List, Optional
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import google.generativeai as genai
from src.shared.base_service import BaseService
from src.shared.api_config import api_config
from src.shared.gemini_config import gemini_config
from datetime import datetime
from fastapi import APIRouter
import re
import json

logger = logging.getLogger(__name__)

router = APIRouter()


class RAGScraperService(BaseService):
    """Service for web scraping and content generation using RAG."""

    def __init__(self):
        """Initialize RAG scraper service."""
        super().__init__("rag_scraper")
        self.model = None
        self.session = None

    async def initialize(self) -> None:
        """Initialize the service and configure Gemini API."""
        try:
            # Initialize API configuration
            await api_config.initialize()

            # Configure Gemini model
            self.model = gemini_config.configure_model("RECOMMENDATION")

            # Create aiohttp session
            self.session = aiohttp.ClientSession()

            self._initialized = True
            logger.info("RAG scraper service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG scraper service: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up service resources."""
        if self.session:
            await self.session.close()
        self.model = None
        await super().cleanup()

    async def health_check(self) -> Dict[str, str]:
        """Check service health.
        
        Returns:
            Dict[str, str]: Health status
        """
        return {
            "status": "healthy" if self._initialized and self.model is not None else "unhealthy"
        }

    async def validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate scraper request.

        Args:
            request: Request to validate

        Returns:
            bool: True if request is valid
        """
        if "query" not in request:
            return False
        if "urls" in request and not isinstance(request["urls"], list):
            return False
        return True

    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a RAG scraper request.

        Args:
            request: Dictionary containing:
                - query: Search query or topic
                - urls: Optional list of URLs to scrape
                - max_results: Maximum number of results (default: 5)
                - include_snippets: Whether to include text snippets (default: True)

        Returns:
            Dict[str, Any]: Scraping and generation results

        Raises:
            ValueError: If request is invalid or processing fails
        """
        try:
            # Get request parameters
            query = request["query"]
            urls = request.get("urls", [])
            max_results = request.get("max_results", 5)
            include_snippets = request.get("include_snippets", True)

            # Scrape content
            scraped_content = await self._scrape_urls(urls) if urls else []

            # Generate content using RAG
            content = await api_config.execute_with_retry(
                self._generate_content,
                query,
                scraped_content,
                max_results,
                include_snippets,
                generation_config=gemini_config.get_generation_config("RECOMMENDATION")
            )

            return {
                "status": "success",
                "content": content,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.service_name,
                    "urls_processed": len(urls),
                },
            }

        except Exception as e:
            logger.error(f"RAG scraping failed: {str(e)}")
            return {"status": "error", "error": str(e), "service": self.service_name}

    async def _scrape_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape content from URLs.

        Args:
            urls: List of URLs to scrape

        Returns:
            List[Dict[str, Any]]: Scraped content
        """
        scraped_content = []
        
        for url in urls:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract main content
                        content = self._extract_main_content(soup)
                        
                        if content:
                            scraped_content.append({
                                "url": url,
                                "title": soup.title.string if soup.title else "",
                                "content": content,
                                "timestamp": datetime.now().isoformat()
                            })
                    else:
                        logger.warning(f"Failed to fetch {url}: {response.status}")
                        
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue
                
        return scraped_content

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            str: Extracted content
        """
        # Remove script and style elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()

        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text

    async def _generate_content(
        self,
        query: str,
        scraped_content: List[Dict[str, Any]],
        max_results: int,
        include_snippets: bool,
        generation_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate content using RAG.

        Args:
            query: User query
            scraped_content: List of scraped content
            max_results: Maximum number of results
            include_snippets: Whether to include text snippets
            generation_config: Generation configuration

        Returns:
            List[Dict[str, Any]]: Generated content
        """
        try:
            # Build context from scraped content
            context = self._build_context(scraped_content, include_snippets)
            
            # Build prompt
            prompt = self._build_generation_prompt(query, context, max_results)

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )

            logger.info("Raw response from model:")
            logger.info(response.text)

            # Parse response
            try:
                # First try to parse as direct JSON
                content = json.loads(response.text)
                if isinstance(content, list):
                    return content[:max_results]
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract structured content
                return self._parse_unstructured_response(response.text, max_results)

        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return [{
                'title': 'Error in Content Generation',
                'description': 'An error occurred while generating content',
                'source': 'system',
                'relevance_score': 0.0,
                'tags': ['error']
            }]

    def _build_context(
        self, scraped_content: List[Dict[str, Any]], include_snippets: bool
    ) -> str:
        """Build context from scraped content.

        Args:
            scraped_content: List of scraped content
            include_snippets: Whether to include text snippets

        Returns:
            str: Formatted context
        """
        context = []
        
        for item in scraped_content:
            context.append(f"Source: {item['url']}")
            if item.get('title'):
                context.append(f"Title: {item['title']}")
            if include_snippets and item.get('content'):
                # Include a snippet of content (first 500 characters)
                snippet = item['content'][:500] + "..."
                context.append(f"Content snippet: {snippet}")
            context.append("")  # Add blank line between sources
            
        return "\n".join(context)

    def _build_generation_prompt(
        self, query: str, context: str, max_results: int
    ) -> str:
        """Build generation prompt.

        Args:
            query: User query
            context: Context from scraped content
            max_results: Maximum number of results

        Returns:
            str: Generation prompt
        """
        return f"""Based on the following context and query, generate {max_results} relevant pieces of content.

Query: {query}

Context:
{context}

For each result, provide the following information in this exact format:

Title: [A clear and relevant title]
Description: [A detailed and informative description]
Source: [Source URL or 'Generated' if no specific source]
Relevance Score: [A number between 0.0 and 1.0]
Tags: [Relevant tags separated by commas]

Important:
- Provide exactly {max_results} results
- Each result must have all the fields mentioned above
- Relevance scores should be between 0.0 and 1.0
- Separate each result with a blank line
- Be informative and accurate
- Properly attribute information to sources when available

Example format:
Title: Understanding Neural Networks
Description: A comprehensive guide to neural network architecture and functionality...
Source: https://example.com/neural-networks
Relevance Score: 0.95
Tags: AI, Machine Learning, Neural Networks, Deep Learning"""

    def _parse_unstructured_response(
        self, response_text: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Parse unstructured response into results.

        Args:
            response_text: Raw response text
            max_results: Maximum number of results

        Returns:
            List[Dict[str, Any]]: Structured results
        """
        results = []
        current_item = {}
        
        for line in response_text.split('\n'):
            line = line.strip()
            
            # Skip empty lines unless we have a complete item
            if not line:
                if current_item and 'title' in current_item:
                    logger.debug(f"Adding complete item: {current_item}")
                    results.append(current_item.copy())
                    current_item = {}
                continue
            
            # Process line if it contains a key-value pair
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                logger.debug(f"Processing line - Key: {key}, Value: {value}")
                
                if key == 'title':
                    # If we already have an item, save it before starting a new one
                    if current_item and 'title' in current_item:
                        results.append(current_item.copy())
                        current_item = {}
                    current_item['title'] = value
                    
                elif key == 'tags':
                    # Parse tags list
                    tags = [t.strip() for t in value.strip('[]').split(',')]
                    current_item['tags'] = tags
                    
                elif key == 'relevance_score':
                    # Parse float score
                    try:
                        score_match = re.search(r'(\d+\.?\d*|\.\d+)', value)
                        if score_match:
                            score = float(score_match.group(1))
                            current_item['relevance_score'] = max(0.0, min(1.0, score))
                        else:
                            current_item['relevance_score'] = 0.5
                    except Exception as e:
                        logger.error(f"Error parsing relevance score: {str(e)}")
                        current_item['relevance_score'] = 0.5
                        
                else:
                    current_item[key] = value
        
        # Add the last item if it exists and has a title
        if current_item and 'title' in current_item:
            logger.debug(f"Adding final item: {current_item}")
            results.append(current_item.copy())
        
        # Ensure all items have required fields
        for item in results:
            if 'relevance_score' not in item:
                item['relevance_score'] = 0.5
            if 'tags' not in item:
                item['tags'] = []
            if 'source' not in item:
                item['source'] = 'Generated'
        
        logger.info(f"Parsed {len(results)} results from unstructured response")
        return results[:max_results]


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
