"""Module for processing single images with Gemini API."""

import os
from typing import Union, BinaryIO
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from .utils import async_retry_with_backoff, logger

class GeminiSingleImage:
    def __init__(self):
        """Initialize the Gemini single image processing module."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro-vision')
        self._logger = logger.getChild('single_image')

    @async_retry_with_backoff()
    async def process_single_image(
        self,
        image: Union[str, Image.Image, BinaryIO],
        prompt: str
    ) -> GenerateContentResponse:
        """Process a single image with a text prompt using retry mechanism.
        
        Args:
            image: Path to image file, PIL Image object, or file-like object
            prompt: Text prompt to guide the image analysis
            
        Returns:
            GenerateContentResponse: The response from Gemini API
            
        Raises:
            ValueError: If image loading fails
            RuntimeError: If API call fails after retries
        """
        try:
            # Validate image first
            self.validate_image(image)
            self._logger.info("Image validation successful")

            # If image is a file path, load it
            if isinstance(image, str):
                self._logger.info(f"Loading image from path: {image}")
                image = Image.open(image)
            
            # Make the API call
            self._logger.info(f"Processing image with prompt: {prompt[:50]}...")
            response = await self.model.generate_content_async([prompt, image])
            self._logger.info("Successfully received response from API")
            return response
            
        except ValueError as e:
            self._logger.error(f"Image validation failed: {str(e)}")
            raise
        except Exception as e:
            self._logger.error(f"Failed to process image: {str(e)}")
            raise RuntimeError(f"Failed to process image: {str(e)}")

    @staticmethod
    def validate_image(image: Union[str, Image.Image, BinaryIO]) -> bool:
        """Validate that an image can be processed.
        
        Args:
            image: Image to validate
            
        Returns:
            bool: True if image is valid
            
        Raises:
            ValueError: If image is invalid
        """
        try:
            if isinstance(image, str):
                Image.open(image)
            elif isinstance(image, Image.Image):
                # Already a PIL Image
                pass
            elif hasattr(image, 'read'):
                Image.open(image)
            else:
                raise ValueError("Invalid image type")
            return True
        except Exception as e:
            raise ValueError(f"Invalid image: {str(e)}") 