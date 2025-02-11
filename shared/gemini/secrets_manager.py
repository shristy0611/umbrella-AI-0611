"""Module for managing API keys using AWS Secrets Manager."""

import os
import json
import boto3
from typing import Dict, Optional
from botocore.exceptions import ClientError
from .utils import logger

class SecretsManager:
    """Class for managing secrets using AWS Secrets Manager."""
    
    def __init__(self):
        """Initialize the secrets manager."""
        self._logger = logger.getChild('secrets_manager')
        self._client = None
        self._secret_name = os.getenv('AWS_SECRET_NAME', 'umbrella/gemini/api-keys')
        self._region = os.getenv('AWS_REGION', 'us-east-1')
        self._environment = os.getenv('ENVIRONMENT', 'development')
        
    def _get_client(self):
        """Get or create AWS Secrets Manager client."""
        if self._client is None:
            self._client = boto3.client(
                service_name='secretsmanager',
                region_name=self._region
            )
        return self._client
    
    def get_secrets(self) -> Dict[str, str]:
        """Get all API keys from AWS Secrets Manager.
        
        Returns:
            Dict[str, str]: Dictionary of API keys
            
        Raises:
            RuntimeError: If unable to retrieve secrets
        """
        if self._environment == 'development':
            self._logger.info("Using environment variables in development mode")
            return self._get_local_secrets()
        
        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=self._secret_name)
            
            if 'SecretString' in response:
                secret = json.loads(response['SecretString'])
                self._logger.info("Successfully retrieved secrets from AWS")
                return secret
            else:
                raise RuntimeError("No SecretString found in response")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self._logger.error(f"Failed to get secrets: {error_code} - {error_message}")
            
            if self._environment != 'production':
                self._logger.warning("Falling back to environment variables")
                return self._get_local_secrets()
            raise RuntimeError(f"Failed to get secrets: {error_message}")
    
    def _get_local_secrets(self) -> Dict[str, str]:
        """Get API keys from environment variables.
        
        Returns:
            Dict[str, str]: Dictionary of API keys from environment
        """
        env_mapping = {
            'GEMINI_API_KEY_OCR': 'ocr_api_key',
            'GEMINI_API_KEY_RECOMMENDATION': 'recommendation_api_key',
            'GEMINI_API_KEY_SENTIMENT': 'sentiment_api_key',
            'GEMINI_API_KEY_CHATBOT': 'chatbot_api_key',
            'ORCHESTRATOR_API_KEY': 'orchestrator_api_key',
            'TASK_DECOMPOSER_API_KEY': 'task_decomposer_api_key',
            'RESULT_VERIFIER_API_KEY': 'result_verifier_api_key',
            'GEMINI_API_KEY': 'default_api_key'
        }
        
        secrets = {}
        for env_var, secret_key in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                secrets[secret_key] = value
        
        return secrets
    
    def update_secret(self, key: str, value: str) -> None:
        """Update a specific secret in AWS Secrets Manager.
        
        Args:
            key: Key of the secret to update
            value: New value for the secret
            
        Raises:
            RuntimeError: If unable to update secret
        """
        if self._environment == 'development':
            self._logger.warning("Secret updates not supported in development mode")
            return
        
        try:
            # Get current secrets
            current_secrets = self.get_secrets()
            
            # Update the specific key
            current_secrets[key] = value
            
            # Save back to AWS
            client = self._get_client()
            client.put_secret_value(
                SecretId=self._secret_name,
                SecretString=json.dumps(current_secrets)
            )
            self._logger.info(f"Successfully updated secret: {key}")
            
        except Exception as e:
            self._logger.error(f"Failed to update secret: {str(e)}")
            raise RuntimeError(f"Failed to update secret: {str(e)}")
    
    def rotate_keys(self, service_key: Optional[str] = None) -> None:
        """Rotate API keys in AWS Secrets Manager.
        
        Args:
            service_key: Optional specific service key to rotate
            
        Raises:
            RuntimeError: If unable to rotate keys
        """
        if self._environment == 'development':
            self._logger.warning("Key rotation not supported in development mode")
            return
        
        try:
            client = self._get_client()
            
            if service_key:
                # Rotate specific key
                client.rotate_secret(
                    SecretId=f"{self._secret_name}/{service_key}",
                    RotationRules={'AutomaticallyAfterDays': 30}
                )
                self._logger.info(f"Initiated rotation for key: {service_key}")
            else:
                # Rotate all keys
                client.rotate_secret(
                    SecretId=self._secret_name,
                    RotationRules={'AutomaticallyAfterDays': 30}
                )
                self._logger.info("Initiated rotation for all keys")
                
        except Exception as e:
            self._logger.error(f"Failed to rotate keys: {str(e)}")
            raise RuntimeError(f"Failed to rotate keys: {str(e)}")

# Global instance
secrets_manager = SecretsManager() 