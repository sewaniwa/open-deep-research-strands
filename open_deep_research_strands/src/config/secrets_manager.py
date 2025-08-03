"""
Secure secrets and API key management system.
"""
import os
import json
import base64
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..exceptions import SecurityError, ConfigurationError
from .logging_config import LoggerMixin


@dataclass
class CredentialEntry:
    """Represents a stored credential."""
    name: str
    value: str
    encrypted: bool = True
    created_at: Optional[str] = None
    last_used: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SecretsManager(LoggerMixin):
    """
    Secure management of API keys and sensitive configuration.
    
    Features:
    - Encryption at rest using Fernet (AES 128)
    - Environment variable fallback
    - Key rotation support
    - Access logging and auditing
    """
    
    def __init__(self, secrets_file: Optional[Path] = None, encryption_key: Optional[bytes] = None):
        """
        Initialize secrets manager.
        
        Args:
            secrets_file: Path to encrypted secrets file
            encryption_key: Optional encryption key (derived from password if not provided)
        """
        self.secrets_file = secrets_file or Path.home() / ".open_deep_research" / "secrets.enc"
        self.credentials: Dict[str, CredentialEntry] = {}
        
        # Initialize encryption
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            self.cipher = self._initialize_encryption()
        
        # Load existing secrets
        self._load_secrets()
        
        self.logger.info("Secrets manager initialized", 
                        secrets_file=str(self.secrets_file),
                        encrypted=True)
    
    def _initialize_encryption(self) -> Fernet:
        """Initialize encryption using password or auto-generated key."""
        key_file = self.secrets_file.parent / "encryption.key"
        
        # Check for existing key
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                return Fernet(key)
            except Exception as e:
                self.logger.warning(f"Failed to load existing key: {e}")
        
        # Generate new key
        password = os.getenv("ODR_ENCRYPTION_PASSWORD")
        if password:
            # Derive key from password
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        else:
            # Generate random key
            key = Fernet.generate_key()
        
        # Save key securely
        key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)  # Read/write for owner only
        
        return Fernet(key)
    
    def _load_secrets(self) -> None:
        """Load secrets from encrypted file."""
        if not self.secrets_file.exists():
            return
        
        try:
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            secrets_data = json.loads(decrypted_data.decode())
            
            for name, data in secrets_data.items():
                self.credentials[name] = CredentialEntry(**data)
            
            self.logger.info(f"Loaded {len(self.credentials)} credentials")
            
        except Exception as e:
            self.logger.error(f"Failed to load secrets: {e}")
            raise SecurityError(f"Failed to load secrets: {str(e)}")
    
    def _save_secrets(self) -> None:
        """Save secrets to encrypted file."""
        try:
            # Prepare data for serialization
            secrets_data = {}
            for name, credential in self.credentials.items():
                secrets_data[name] = {
                    "name": credential.name,
                    "value": credential.value,
                    "encrypted": credential.encrypted,
                    "created_at": credential.created_at,
                    "last_used": credential.last_used,
                    "metadata": credential.metadata or {}
                }
            
            # Encrypt and save
            data_bytes = json.dumps(secrets_data).encode()
            encrypted_data = self.cipher.encrypt(data_bytes)
            
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(self.secrets_file, 0o600)  # Read/write for owner only
            
            self.logger.info(f"Saved {len(self.credentials)} credentials")
            
        except Exception as e:
            self.logger.error(f"Failed to save secrets: {e}")
            raise SecurityError(f"Failed to save secrets: {str(e)}")
    
    def store_credential(self, name: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a new credential.
        
        Args:
            name: Credential name/identifier
            value: Credential value (API key, token, etc.)
            metadata: Optional metadata
        """
        from datetime import datetime
        
        # Validate inputs
        if not name or not value:
            raise SecurityError("Credential name and value cannot be empty")
        
        # Store credential
        self.credentials[name] = CredentialEntry(
            name=name,
            value=value,
            encrypted=True,
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        
        self._save_secrets()
        self.logger.info(f"Stored credential: {name}")
    
    def get_credential(self, name: str, fallback_env: Optional[str] = None) -> Optional[str]:
        """
        Get a credential value.
        
        Args:
            name: Credential name
            fallback_env: Environment variable to check if credential not found
            
        Returns:
            Credential value or None if not found
        """
        from datetime import datetime
        
        # Check stored credentials first
        if name in self.credentials:
            credential = self.credentials[name]
            credential.last_used = datetime.utcnow().isoformat()
            self._save_secrets()
            self.logger.debug(f"Retrieved credential: {name}")
            return credential.value
        
        # Fallback to environment variable
        if fallback_env:
            env_value = os.getenv(fallback_env)
            if env_value:
                self.logger.debug(f"Retrieved credential from environment: {fallback_env}")
                return env_value
        
        # Check common environment variable patterns
        common_patterns = [name.upper(), f"ODR_{name.upper()}", f"{name.upper()}_API_KEY"]
        for pattern in common_patterns:
            env_value = os.getenv(pattern)
            if env_value:
                self.logger.debug(f"Retrieved credential from environment: {pattern}")
                return env_value
        
        self.logger.warning(f"Credential not found: {name}")
        return None
    
    def remove_credential(self, name: str) -> bool:
        """
        Remove a credential.
        
        Args:
            name: Credential name
            
        Returns:
            True if credential was removed
        """
        if name in self.credentials:
            del self.credentials[name]
            self._save_secrets()
            self.logger.info(f"Removed credential: {name}")
            return True
        return False
    
    def list_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        List all stored credentials (without values).
        
        Returns:
            Dictionary of credential metadata
        """
        result = {}
        for name, credential in self.credentials.items():
            result[name] = {
                "name": credential.name,
                "encrypted": credential.encrypted,
                "created_at": credential.created_at,
                "last_used": credential.last_used,
                "metadata": credential.metadata or {}
            }
        return result
    
    def rotate_encryption_key(self, new_password: Optional[str] = None) -> None:
        """
        Rotate the encryption key.
        
        Args:
            new_password: New password for key derivation
        """
        # Store current credentials in memory
        temp_credentials = self.credentials.copy()
        
        # Generate new cipher
        if new_password:
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(new_password.encode()))
        else:
            key = Fernet.generate_key()
        
        self.cipher = Fernet(key)
        
        # Re-save with new encryption
        self.credentials = temp_credentials
        self._save_secrets()
        
        # Update key file
        key_file = self.secrets_file.parent / "encryption.key"
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        
        self.logger.info("Encryption key rotated successfully")


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance."""
    global _secrets_manager
    
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    
    return _secrets_manager


def get_api_key(provider: str, fallback_env: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get API keys.
    
    Args:
        provider: Provider name (openai, anthropic, etc.)
        fallback_env: Environment variable fallback
        
    Returns:
        API key or None if not found
    """
    manager = get_secrets_manager()
    return manager.get_credential(f"{provider}_api_key", fallback_env)


def store_api_key(provider: str, api_key: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Convenience function to store API keys.
    
    Args:
        provider: Provider name
        api_key: API key value
        metadata: Optional metadata
    """
    manager = get_secrets_manager()
    manager.store_credential(f"{provider}_api_key", api_key, metadata)