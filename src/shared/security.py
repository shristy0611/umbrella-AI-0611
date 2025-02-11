"""Security management module for UMBRELLA-AI."""

import os
import jwt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security operations like authentication and authorization."""
    
    def __init__(self):
        """Initialize security manager."""
        self.secret_key = os.getenv("JWT_SECRET_KEY", "development-secret-key")
        self.token_expiry = int(os.getenv("TOKEN_EXPIRY_MINUTES", "60"))
        
    def create_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT token.
        
        Args:
            data: Data to encode in token
            
        Returns:
            str: JWT token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.token_expiry)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Optional[Dict[str, Any]]: Decoded token data if valid
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None
            
    def hash_password(self, password: str) -> str:
        """Hash a password.
        
        Args:
            password: Password to hash
            
        Returns:
            str: Hashed password
        """
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
        
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            plain: Password to verify
            hashed: Hash to verify against
            
        Returns:
            bool: True if password matches hash
        """
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain, hashed) 