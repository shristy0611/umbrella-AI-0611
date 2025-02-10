"""Module for processing multiple images with Gemini API."""

import os
import base64
from typing import List, Union, BinaryIO
import requests
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from .utils import async_retry_with_backoff, logger

class GeminiMultiImage:
    def __init__(self):
        """Initialize the Gemini multiple image processing module."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro-vision')
        self._logger = logger.getChild('multi_image')

    @async_retry_with_backoff()
    async def process_multiple_images(
        self,
        images: List[Union[str, Image.Image, BinaryIO]],
        prompt: str
    ) -> GenerateContentResponse:
        """Process multiple images with a text prompt using retry mechanism.
        
        Args:
            images: List of image sources (file paths, PIL Images, or file-like objects)
            prompt: Text prompt to guide the image analysis
            
        Returns:
            GenerateContentResponse: The response from Gemini API
            
        Raises:
            ValueError: If image loading fails
            RuntimeError: If API call fails after retries
        """
        try:
            # Validate all images first
            self.validate_images(images)
            self._logger.info("All images validated successfully")

            processed_images = []
            for i, img in enumerate(images):
                if isinstance(img, str):
                    # Handle URLs
                    if img.startswith(('http://', 'https://')):
                        self._logger.info(f"Downloading image {i+1} from URL: {img}")
                        response = requests.get(img)
                        response.raise_for_status()
                        img = Image.open(requests.get(img).raw)
                    else:
                        # Local file path
                        self._logger.info(f"Loading image {i+1} from path: {img}")
                        img = Image.open(img)
                processed_images.append(img)
            
            # Make the API call with all processed images
            self._logger.info(f"Processing {len(processed_images)} images with prompt: {prompt[:50]}...")
            response = await self.model.generate_content_async([prompt, *processed_images])
            self._logger.info("Successfully received response from API")
            return response
            
        except ValueError as e:
            self._logger.error(f"Image validation failed: {str(e)}")
            raise
        except requests.RequestException as e:
            self._logger.error(f"Failed to download image: {str(e)}")
            raise RuntimeError(f"Failed to download image: {str(e)}")
        except Exception as e:
            self._logger.error(f"Failed to process images: {str(e)}")
            raise RuntimeError(f"Failed to process images: {str(e)}")

    @staticmethod
    def validate_images(images: List[Union[str, Image.Image, BinaryIO]]) -> bool:
        """Validate that all images can be processed.
        
        Args:
            images: List of images to validate
            
        Returns:
            bool: True if all images are valid
            
        Raises:
            ValueError: If any image is invalid
        """
        for i, img in enumerate(images):
            try:
                if isinstance(img, str):
                    if img.startswith(('http://', 'https://')):
                        response = requests.get(img)
                        response.raise_for_status()
                        Image.open(requests.get(img).raw)
                    else:
                        Image.open(img)
                elif isinstance(img, Image.Image):
                    # Already a PIL Image
                    pass
                elif hasattr(img, 'read'):
                    Image.open(img)
                else:
                    raise ValueError(f"Invalid image type for image {i+1}")
            except Exception as e:
                raise ValueError(f"Invalid image {i+1}: {str(e)}")
        return True 