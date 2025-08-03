"""
Local file-based memory system for development.
"""
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import hashlib

# Try to import aiofiles, fall back to regular file operations
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from ..config.logging_config import LoggerMixin


@dataclass
class MemoryEntry:
    """Represents a single memory entry."""
    id: str
    namespace: str
    content: Any
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if not self.expires_at:
            return False
        
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.utcnow() > expires
        except ValueError:
            return False


class LocalMemorySystem(LoggerMixin):
    """File-based local memory system for development."""
    
    def __init__(self, config):
        """
        Initialize local memory system.
        
        Args:
            config: Memory configuration object
        """
        self.config = config
        self.storage_path = Path(config.storage_path)
        self.namespaces: Dict[str, Dict[str, MemoryEntry]] = {}
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.sessions_path = self.storage_path / "sessions"
        self.cache_path = self.storage_path / "cache"
        
        self.sessions_path.mkdir(exist_ok=True)
        self.cache_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Local memory system initialized - storage_path={str(self.storage_path)}")
    
    async def create_namespace(self, namespace: str, **options) -> str:
        """
        Create a new memory namespace.
        
        Args:
            namespace: Namespace identifier
            **options: Additional options (retention_policy, max_size, etc.)
            
        Returns:
            Namespace identifier
        """
        if namespace not in self.namespaces:
            self.namespaces[namespace] = {}
            
            # Save namespace metadata
            namespace_file = self.sessions_path / f"{namespace}.json"
            metadata = {
                "namespace": namespace,
                "created_at": datetime.utcnow().isoformat(),
                "options": options,
                "entry_count": 0
            }
            
            if HAS_AIOFILES:
                async with aiofiles.open(namespace_file, 'w') as f:
                    await f.write(json.dumps(metadata, indent=2))
            else:
                with open(namespace_file, 'w') as f:
                    f.write(json.dumps(metadata, indent=2))
            
            self.logger.info(f"Created memory namespace - namespace={namespace}")
        
        return namespace
    
    async def store(self, namespace: str, key: str, content: Any, 
                   metadata: Dict[str, Any] = None, ttl: int = None) -> str:
        """
        Store content in memory.
        
        Args:
            namespace: Memory namespace
            key: Storage key
            content: Content to store
            metadata: Optional metadata
            ttl: Time-to-live in seconds
            
        Returns:
            Entry ID
        """
        if namespace not in self.namespaces:
            await self.create_namespace(namespace)
        
        # Generate entry ID
        entry_id = self._generate_entry_id(namespace, key)
        
        # Calculate expiration
        expires_at = None
        if ttl:
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()
        
        # Create memory entry
        entry = MemoryEntry(
            id=entry_id,
            namespace=namespace,
            content=content,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            expires_at=expires_at
        )
        
        # Store in memory
        self.namespaces[namespace][key] = entry
        
        # Persist to file
        await self._persist_entry(entry)
        
        self.logger.debug(f"Stored memory entry - namespace={namespace}, key={key}, entry_id={entry_id}")
        
        return entry_id
    
    async def retrieve(self, namespace: str, key: str) -> Optional[Any]:
        """
        Retrieve content from memory.
        
        Args:
            namespace: Memory namespace
            key: Storage key
            
        Returns:
            Stored content or None if not found
        """
        if namespace not in self.namespaces:
            # Try loading from disk
            await self._load_namespace(namespace)
        
        if namespace not in self.namespaces:
            return None
        
        if key not in self.namespaces[namespace]:
            return None
        
        entry = self.namespaces[namespace][key]
        
        # Check if expired
        if entry.is_expired():
            await self.delete(namespace, key)
            return None
        
        # Update access time
        entry.metadata["last_accessed"] = datetime.utcnow().isoformat()
        await self._persist_entry(entry)
        
        return entry.content
    
    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete entry from memory.
        
        Args:
            namespace: Memory namespace
            key: Storage key
            
        Returns:
            True if deleted, False if not found
        """
        if namespace not in self.namespaces:
            return False
        
        if key not in self.namespaces[namespace]:
            return False
        
        entry = self.namespaces[namespace][key]
        
        # Remove from memory
        del self.namespaces[namespace][key]
        
        # Remove file
        entry_file = self._get_entry_file_path(entry.id)
        if entry_file.exists():
            entry_file.unlink()
        
        self.logger.debug(f"Deleted memory entry - namespace={namespace}, key={key}")
        return True
    
    async def list_entries(self, namespace: str) -> List[str]:
        """
        List all keys in a namespace.
        
        Args:
            namespace: Memory namespace
            
        Returns:
            List of keys
        """
        if namespace not in self.namespaces:
            await self._load_namespace(namespace)
        
        if namespace not in self.namespaces:
            return []
        
        # Filter out expired entries
        valid_keys = []
        for key, entry in list(self.namespaces[namespace].items()):
            if entry.is_expired():
                await self.delete(namespace, key)
            else:
                valid_keys.append(key)
        
        return valid_keys
    
    async def search(self, namespace: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Simple text-based search in memory content.
        
        Args:
            namespace: Memory namespace
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching entries with metadata
        """
        if namespace not in self.namespaces:
            await self._load_namespace(namespace)
        
        if namespace not in self.namespaces:
            return []
        
        results = []
        query_lower = query.lower()
        
        for key, entry in self.namespaces[namespace].items():
            if entry.is_expired():
                continue
            
            # Simple text search in content
            content_str = str(entry.content).lower()
            if query_lower in content_str:
                results.append({
                    "key": key,
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "score": content_str.count(query_lower)  # Simple relevance score
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    async def cleanup_expired(self, namespace: str = None) -> int:
        """
        Clean up expired entries.
        
        Args:
            namespace: Optional specific namespace to clean
            
        Returns:
            Number of entries cleaned up
        """
        cleaned_count = 0
        
        namespaces_to_clean = [namespace] if namespace else list(self.namespaces.keys())
        
        for ns in namespaces_to_clean:
            if ns not in self.namespaces:
                continue
            
            for key, entry in list(self.namespaces[ns].items()):
                if entry.is_expired():
                    await self.delete(ns, key)
                    cleaned_count += 1
        
        self.logger.info(f"Cleaned up expired entries - count={cleaned_count}")
        return cleaned_count
    
    def _generate_entry_id(self, namespace: str, key: str) -> str:
        """Generate unique entry ID."""
        content = f"{namespace}:{key}:{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_entry_file_path(self, entry_id: str) -> Path:
        """Get file path for entry."""
        return self.cache_path / f"{entry_id}.json"
    
    async def _persist_entry(self, entry: MemoryEntry):
        """Persist entry to disk."""
        entry_file = self._get_entry_file_path(entry.id)
        
        if HAS_AIOFILES:
            async with aiofiles.open(entry_file, 'w') as f:
                await f.write(json.dumps(entry.to_dict(), indent=2))
        else:
            with open(entry_file, 'w') as f:
                f.write(json.dumps(entry.to_dict(), indent=2))
    
    async def _load_namespace(self, namespace: str):
        """Load namespace from disk."""
        namespace_file = self.sessions_path / f"{namespace}.json"
        
        if not namespace_file.exists():
            return
        
        try:
            if HAS_AIOFILES:
                async with aiofiles.open(namespace_file, 'r') as f:
                    metadata = json.loads(await f.read())
            else:
                with open(namespace_file, 'r') as f:
                    metadata = json.loads(f.read())
            
            # Load entries
            self.namespaces[namespace] = {}
            
            # Find all entry files for this namespace
            for entry_file in self.cache_path.glob("*.json"):
                try:
                    if HAS_AIOFILES:
                        async with aiofiles.open(entry_file, 'r') as f:
                            entry_data = json.loads(await f.read())
                    else:
                        with open(entry_file, 'r') as f:
                            entry_data = json.loads(f.read())
                    
                    if entry_data.get("namespace") == namespace:
                        entry = MemoryEntry.from_dict(entry_data)
                        # Extract key from metadata or generate from content
                        key = entry.metadata.get("original_key", entry.id)
                        self.namespaces[namespace][key] = entry
                        
                except Exception as e:
                    self.logger.warning(f"Failed to load entry {entry_file}: {e}")
            
            self.logger.debug(f"Loaded namespace from disk - namespace={namespace}, entries={len(self.namespaces[namespace])}")
            
        except Exception as e:
            self.logger.error(f"Failed to load namespace {namespace}: {e}")
    
    async def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """Get statistics for a namespace."""
        if namespace not in self.namespaces:
            await self._load_namespace(namespace)
        
        if namespace not in self.namespaces:
            return {"exists": False}
        
        entries = self.namespaces[namespace]
        
        return {
            "exists": True,
            "total_entries": len(entries),
            "expired_entries": sum(1 for entry in entries.values() if entry.is_expired()),
            "storage_size": await self._calculate_namespace_size(namespace)
        }
    
    async def _calculate_namespace_size(self, namespace: str) -> int:
        """Calculate storage size for namespace in bytes."""
        total_size = 0
        
        for entry in self.namespaces[namespace].values():
            entry_file = self._get_entry_file_path(entry.id)
            if entry_file.exists():
                total_size += entry_file.stat().st_size
        
        return total_size