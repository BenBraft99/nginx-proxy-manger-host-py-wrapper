"""
Nginx Proxy Manager API Client

A Python client library for interacting with the Nginx Proxy Manager API.
Provides methods for managing proxy hosts with automatic SSL certificate generation.
"""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json


class NginxProxyManagerError(Exception):
    """Base exception for Nginx Proxy Manager API errors"""
    pass


class AuthenticationError(NginxProxyManagerError):
    """Raised when authentication fails"""
    pass


class APIError(NginxProxyManagerError):
    """Raised when API request fails"""
    pass


class NginxProxyManagerClient:
    """
    Main client class for Nginx Proxy Manager API.
    
    Example:
        client = NginxProxyManagerClient(
            host="http://localhost:81",
            username="admin@example.com",
            password="changeme"
        )
        
        # Create a proxy host with SSL
        host = client.create_proxy_host(
            domain_name="app.example.com",
            forward_host="192.168.1.100",
            forward_port=8080
        )
        
        # Rename a proxy host
        client.rename_proxy_host(host['id'], "newapp.example.com")
        
        # Delete a proxy host
        client.delete_proxy_host(host['id'])
    """
    
    def __init__(self, host: str, username: str, password: str):
        """
        Initialize the Nginx Proxy Manager client.
        
        Args:
            host: The base URL of the Nginx Proxy Manager instance (e.g., "http://localhost:81")
            username: The username/email for authentication
            password: The password for authentication
        """
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.token_expires = None
        self._session = requests.Session()
        
        # Authenticate on initialization
        self._authenticate()
    
    def _authenticate(self) -> None:
        """
        Authenticate with the Nginx Proxy Manager API and obtain a JWT token.
        
        Raises:
            AuthenticationError: If authentication fails
        """
        url = f"{self.host}/api/tokens"
        payload = {
            "identity": self.username,
            "secret": self.password
        }
        
        try:
            response = self._session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            self.token = data['token']
            # Token typically expires in 1 day, refresh before that
            self.token_expires = datetime.now() + timedelta(hours=23)
            
            # Set the authorization header for future requests
            self._session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    def _check_token(self) -> None:
        """Check if token is expired and refresh if needed"""
        if self.token_expires and datetime.now() >= self.token_expires:
            self._authenticate()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response data
            
        Raises:
            APIError: If the request fails
        """
        self._check_token()
        
        url = f"{self.host}/api{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Some endpoints return boolean or empty response
            if response.status_code == 204 or not response.content:
                return True
                
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Try to extract detailed error message
            error_msg = f"HTTP {e.response.status_code}: {str(e)}"
            try:
                error_data = e.response.json()
                if 'error' in error_data:
                    error_msg = f"{error_msg}\nDetails: {error_data['error']}"
                elif 'message' in error_data:
                    error_msg = f"{error_msg}\nDetails: {error_data['message']}"
            except:
                # If we can't parse JSON, show raw response text
                if e.response.text:
                    error_msg = f"{error_msg}\nResponse: {e.response.text[:500]}"
            raise APIError(error_msg)
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def create_proxy_host(
        self,
        domain_name: str,
        forward_host: str,
        forward_port: int,
        forward_scheme: str = "http",
        additional_domain_names: Optional[List[str]] = None,
        block_exploits: bool = True,
        http2_support: bool = True,
        ssl_forced: bool = True,
        hsts_enabled: bool = True,
        hsts_subdomains: bool = False,
        allow_websocket_upgrade: bool = True,
        caching_enabled: bool = False,
        access_list_id: int = 0,
        advanced_config: str = "",
        locations: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Create a new proxy host with automatic SSL certificate generation.
        
        Args:
            domain_name: Primary domain name for the proxy host
            forward_host: The hostname/IP to forward requests to
            forward_port: The port to forward requests to
            forward_scheme: The scheme to use when forwarding (http or https)
            additional_domain_names: Additional domain names for this proxy host
            block_exploits: Enable blocking of common exploits
            http2_support: Enable HTTP/2 support
            ssl_forced: Force SSL (redirect HTTP to HTTPS)
            hsts_enabled: Enable HSTS (HTTP Strict Transport Security)
            hsts_subdomains: Include subdomains in HSTS
            allow_websocket_upgrade: Allow WebSocket connections
            caching_enabled: Enable caching
            access_list_id: ID of access list (0 for none)
            advanced_config: Advanced Nginx configuration
            locations: Custom location blocks
            
        Returns:
            Dict containing the created proxy host details
            
        Raises:
            APIError: If creation fails
        """
        # Combine domain names
        domain_names = [domain_name]
        if additional_domain_names:
            domain_names.extend(additional_domain_names)
        
        payload = {
            "domain_names": domain_names,
            "forward_scheme": forward_scheme,
            "forward_host": forward_host,
            "forward_port": forward_port,
            "certificate_id": "new",  # Request new SSL certificate
            "ssl_forced": ssl_forced,
            "hsts_enabled": hsts_enabled,
            "hsts_subdomains": hsts_subdomains,
            "http2_support": http2_support,
            "block_exploits": block_exploits,
            "caching_enabled": caching_enabled,
            "allow_websocket_upgrade": allow_websocket_upgrade,
            "access_list_id": access_list_id,
            "advanced_config": advanced_config,
            "locations": locations or [],
            "enabled": True,
            "meta": {
                "letsencrypt_agree": True,
                "letsencrypt_email": self.username,  # Use the username as the Let's Encrypt email
                "dns_challenge": False
            }
        }
        
        return self._request('POST', '/nginx/proxy-hosts', json=payload)
    
    def get_proxy_host(self, host_id: int, expand: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get details of a specific proxy host.
        
        Args:
            host_id: The ID of the proxy host
            expand: List of related objects to expand (e.g., ['certificate', 'owner'])
            
        Returns:
            Dict containing the proxy host details
            
        Raises:
            APIError: If the request fails
        """
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        return self._request('GET', f'/nginx/proxy-hosts/{host_id}', params=params)
    
    def get_all_proxy_hosts(
        self,
        expand: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all proxy hosts.
        
        Args:
            expand: List of related objects to expand (e.g., ['certificate', 'owner'])
            query: Search query string
            
        Returns:
            List of proxy host dictionaries
            
        Raises:
            APIError: If the request fails
        """
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        if query:
            params['query'] = query
        
        return self._request('GET', '/nginx/proxy-hosts', params=params)
    
    def update_proxy_host(
        self,
        host_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update an existing proxy host.
        
        Args:
            host_id: The ID of the proxy host to update
            **kwargs: Fields to update (domain_names, forward_host, forward_port, etc.)
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If the update fails
        """
        # Get current host data first
        current_host = self.get_proxy_host(host_id)
        
        # Merge with updates
        payload = {
            "domain_names": current_host['domain_names'],
            "forward_scheme": current_host['forward_scheme'],
            "forward_host": current_host['forward_host'],
            "forward_port": current_host['forward_port'],
            "certificate_id": current_host['certificate_id'],            "ssl_forced": current_host['ssl_forced'],
            "hsts_enabled": current_host['hsts_enabled'],
            "hsts_subdomains": current_host['hsts_subdomains'],
            "http2_support": current_host['http2_support'],
            "block_exploits": current_host['block_exploits'],
            "caching_enabled": current_host['caching_enabled'],
            "allow_websocket_upgrade": current_host['allow_websocket_upgrade'],
            "access_list_id": current_host['access_list_id'],
            "advanced_config": current_host['advanced_config'],
            "locations": current_host.get('locations', []),
            "enabled": current_host['enabled'],
            "meta": current_host.get('meta', {})
        }
        
        # Update with provided kwargs
        payload.update(kwargs)
        
        return self._request('PUT', f'/nginx/proxy-hosts/{host_id}', json=payload)
    
    def rename_proxy_host(
        self,
        host_id: int,
        new_domain_name: str,
        additional_domain_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Rename a proxy host (change its domain names).
        
        Args:
            host_id: The ID of the proxy host to rename
            new_domain_name: New primary domain name
            additional_domain_names: Additional domain names
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If the rename fails
        """
        domain_names = [new_domain_name]
        if additional_domain_names:
            domain_names.extend(additional_domain_names)
        
        return self.update_proxy_host(host_id, domain_names=domain_names)
    
    def delete_proxy_host(self, host_id: int) -> bool:
        """
        Delete a proxy host.
        
        Args:
            host_id: The ID of the proxy host to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            APIError: If deletion fails
        """
        return self._request('DELETE', f'/nginx/proxy-hosts/{host_id}')
    
    def enable_proxy_host(self, host_id: int) -> bool:
        """
        Enable a proxy host.
        
        Args:
            host_id: The ID of the proxy host to enable
            
        Returns:
            True if successful
            
        Raises:
            APIError: If the request fails
        """
        return self._request('POST', f'/nginx/proxy-hosts/{host_id}/enable')
    
    def disable_proxy_host(self, host_id: int) -> bool:
        """
        Disable a proxy host.
        
        Args:
            host_id: The ID of the proxy host to disable
            
        Returns:
            True if successful
            
        Raises:
            APIError: If the request fails
        """
        return self._request('POST', f'/nginx/proxy-hosts/{host_id}/disable')
    
    def get_certificates(self) -> List[Dict[str, Any]]:
        """
        Get all SSL certificates.
        
        Returns:
            List of certificate dictionaries
            
        Raises:
            APIError: If the request fails
        """
        return self._request('GET', '/nginx/certificates')
    
    def delete_certificate(self, certificate_id: int) -> bool:
        """
        Delete an SSL certificate.
        
        Args:
            certificate_id: The ID of the certificate to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            APIError: If deletion fails
        """
        return self._request('DELETE', f'/nginx/certificates/{certificate_id}')
    
    def close(self) -> None:
        """Close the session"""
        self._session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
