"""
Shared API clients for external services.
"""

from shared.clients.replicate_client import ReplicateClient
from shared.clients.storage_client import StorageClient, storage_client

__all__ = [
    'ReplicateClient',
    'StorageClient',
    'storage_client',  # Singleton instance for convenience
]