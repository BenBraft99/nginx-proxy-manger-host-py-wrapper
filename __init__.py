"""
Nginx Proxy Manager Python Client Library
"""

from .npm_client import (
    NginxProxyManagerClient,
    NginxProxyManagerError,
    AuthenticationError,
    APIError
)

__version__ = "1.0.0"
__all__ = [
    "NginxProxyManagerClient",
    "NginxProxyManagerError",
    "AuthenticationError",
    "APIError"
]
