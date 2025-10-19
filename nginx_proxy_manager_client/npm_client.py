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
    
    def __init__(self, host: str, username: str, password: str, debug: bool = False):
        """
        Initialize the Nginx Proxy Manager client.
        
        Args:
            host: The base URL of the Nginx Proxy Manager instance (e.g., "http://localhost:81")
            username: The username/email for authentication
            password: The password for authentication
            debug: Enable debug output (prints request/response details)
        """
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.token_expires = None
        self._session = requests.Session()
        self.debug = debug
        
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
        
        if self.debug:
            print(f"\n[DEBUG] {method} {url}")
            if 'json' in kwargs:
                print(f"[DEBUG] Payload: {json.dumps(kwargs['json'], indent=2)}")
        
        try:
            response = self._session.request(method, url, **kwargs)
            
            if self.debug:
                print(f"[DEBUG] Response Status: {response.status_code}")
                if response.content:
                    try:
                        print(f"[DEBUG] Response Body: {json.dumps(response.json(), indent=2)}")
                    except:
                        print(f"[DEBUG] Response Body: {response.text[:500]}")
            
            response.raise_for_status()
            
            # Debug output
            if self.debug:
                print(f"Request {method} {url} - Response {response.status_code}: {response.text}")
            
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
    
    def get_all_certificates(self, expand: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get all SSL certificates.
        
        Args:
            expand: List of related objects to expand
            
        Returns:
            List of certificate dictionaries
            
        Raises:
            APIError: If the request fails
        """
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        return self._request('GET', '/nginx/certificates', params=params)
    
    def find_certificate_by_domains(self, domain_names: List[str]) -> Optional[Dict[str, Any]]:
        """
        Find an existing certificate that matches the given domain names.
        
        This helps avoid Let's Encrypt rate limits by reusing existing certificates.
        
        Args:
            domain_names: List of domain names to match
            
        Returns:
            Certificate dict if found, None otherwise
            
        Raises:
            APIError: If the request fails
        """
        # Normalize and sort domain names for comparison
        domain_names_sorted = sorted([d.lower().strip() for d in domain_names])
        
        try:
            certificates = self.get_all_certificates()
            
            for cert in certificates:
                if cert.get('provider') != 'letsencrypt':
                    continue
                    
                cert_domains = cert.get('domain_names', [])
                cert_domains_sorted = sorted([d.lower().strip() for d in cert_domains])
                  # Check if domains match exactly
                if cert_domains_sorted == domain_names_sorted:
                    if self.debug:
                        print(f"[DEBUG] Found existing certificate ID {cert['id']} for domains: {', '.join(domain_names)}")
                    return cert
            
            if self.debug:
                print(f"[DEBUG] No existing certificate found for domains: {', '.join(domain_names)}")
            return None
            
        except APIError as e:
            if self.debug:
                print(f"[DEBUG] Error searching for certificates: {e}")
            return None
    
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
        locations: Optional[List[Dict]] = None,
        certificate_id: Optional[int] = None,
        letsencrypt_email: Optional[str] = None,
        reuse_certificate: bool = True
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
            certificate_id: Existing certificate ID to use, or None to request new SSL cert
            letsencrypt_email: Email for Let's Encrypt notifications (defaults to username)
            reuse_certificate: If True, check for existing certificate before requesting new one
                              (helps avoid Let's Encrypt rate limits)
            
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
            "enabled": True        }
        
        # Handle SSL certificate
        request_new_cert = certificate_id is None
        
        if request_new_cert:
            # Check if we should reuse an existing certificate
            if reuse_certificate:
                existing_cert = self.find_certificate_by_domains(domain_names)
                if existing_cert:
                    # Reuse existing certificate to avoid rate limits
                    payload["certificate_id"] = existing_cert['id']
                    payload["meta"] = {}
                    request_new_cert = False  # Don't request a new one
                    if self.debug:
                        print(f"[DEBUG] Reusing existing certificate ID {existing_cert['id']}")
            
            # If we still need to request a new certificate
            if request_new_cert:
                # Request new SSL certificate
                payload["certificate_id"] = "new"
                payload["meta"] = {
                    "letsencrypt_agree": True,
                    "letsencrypt_email": letsencrypt_email or self.username,
                    "dns_challenge": False
                }
                if self.debug:
                    print(f"[DEBUG] Requesting new SSL certificate for {', '.join(domain_names)}")
        else:
            # Use existing certificate or no certificate (0)
            payload["certificate_id"] = certificate_id
            payload["meta"] = {}
        
        # Create the proxy host
        result = self._request('POST', '/nginx/proxy-hosts', json=payload)
        
        # If we requested a new certificate, the SSL settings (ssl_forced, hsts_enabled, http2_support)
        # are cleared by the backend's cleanSslHstsData function during initial creation.
        # We need to update the host after creation to enable these settings.
        if request_new_cert and result.get('certificate_id'):
            # Certificate was created successfully, now update to enable SSL settings
            update_payload = {}
            
            if ssl_forced:
                update_payload["ssl_forced"] = True
            if hsts_enabled:
                update_payload["hsts_enabled"] = True
                if hsts_subdomains:
                    update_payload["hsts_subdomains"] = True
            if http2_support:
                update_payload["http2_support"] = True
            
            # Only update if there are settings to change
            if update_payload:
                result = self._request('PUT', f'/nginx/proxy-hosts/{result["id"]}', json=update_payload)
        
        return result
    
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
    
    def get_all_proxy_hosts(self, expand: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get all proxy hosts.
        
        Args:
            expand: List of related objects to expand (e.g., ['certificate', 'owner'])
            
        Returns:
            List of proxy host dictionaries
            
        Raises:
            APIError: If the request fails
        """
        params = {}
        if expand:
            params['expand'] = ','.join(expand)
        
        return self._request('GET', '/nginx/proxy-hosts', params=params)
    
    def update_proxy_host(
        self,
        host_id: int,
        domain_name: Optional[str] = None,
        forward_host: Optional[str] = None,
        forward_port: Optional[int] = None,
        forward_scheme: Optional[str] = None,
        additional_domain_names: Optional[List[str]] = None,
        block_exploits: Optional[bool] = None,
        http2_support: Optional[bool] = None,
        ssl_forced: Optional[bool] = None,
        hsts_enabled: Optional[bool] = None,
        hsts_subdomains: Optional[bool] = None,
        allow_websocket_upgrade: Optional[bool] = None,
        caching_enabled: Optional[bool] = None,
        access_list_id: Optional[int] = None,
        advanced_config: Optional[str] = None,
        locations: Optional[List[Dict]] = None,
        certificate_id: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing proxy host.
        
        Args:
            host_id: The ID of the proxy host to update
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
            access_list_id: ID of access list
            advanced_config: Advanced Nginx configuration
            locations: Custom location blocks
            certificate_id: Certificate ID to use, or "new" to request new SSL cert
            enabled: Enable or disable the host
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If update fails
        """        # Build payload with only provided parameters
        payload = {}
        
        if domain_name is not None or additional_domain_names is not None:
            domain_names = []
            if domain_name:
                domain_names.append(domain_name)
            if additional_domain_names:
                domain_names.extend(additional_domain_names)
            payload["domain_names"] = domain_names
        
        if forward_host is not None:
            payload["forward_host"] = forward_host
        if forward_port is not None:
            payload["forward_port"] = forward_port
        if forward_scheme is not None:
            payload["forward_scheme"] = forward_scheme
        if ssl_forced is not None:
            payload["ssl_forced"] = ssl_forced
        if hsts_enabled is not None:
            payload["hsts_enabled"] = hsts_enabled
        if hsts_subdomains is not None:
            payload["hsts_subdomains"] = hsts_subdomains
        if http2_support is not None:
            payload["http2_support"] = http2_support
        if block_exploits is not None:
            payload["block_exploits"] = block_exploits
        if caching_enabled is not None:
            payload["caching_enabled"] = caching_enabled
        if allow_websocket_upgrade is not None:
            payload["allow_websocket_upgrade"] = allow_websocket_upgrade
        if access_list_id is not None:
            payload["access_list_id"] = access_list_id
        if advanced_config is not None:
            payload["advanced_config"] = advanced_config
        if locations is not None:
            payload["locations"] = locations
        if certificate_id is not None:
            payload["certificate_id"] = certificate_id
        if enabled is not None:
            payload["enabled"] = enabled
        
        return self._request('PUT', f'/nginx/proxy-hosts/{host_id}', json=payload)
    
    def rename_proxy_host(
        self,
        host_id: int,
        new_domain_name: str,
        additional_domain_names: Optional[List[str]] = None,
        renew_certificate: bool = True,
        reuse_certificate: bool = True
    ) -> Dict[str, Any]:
        """
        Rename a proxy host (change its domain name).
        
        IMPORTANT: If the proxy host has an SSL certificate, you should renew it
        because SSL certificates are domain-specific. By default, this function
        will request a new certificate for the new domain name.
        
        Args:
            host_id: The ID of the proxy host to rename
            new_domain_name: The new primary domain name
            additional_domain_names: Additional domain names for this proxy host
            renew_certificate: If True and the host has an SSL cert, request a new one
                              for the new domain name (default: True)
            reuse_certificate: If True, check for existing certificate before requesting new one
                              (helps avoid Let's Encrypt rate limits)
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If rename fails
        """
        domain_names = [new_domain_name]
        if additional_domain_names:
            domain_names.extend(additional_domain_names)
        
        # First, check if the host has an SSL certificate
        current_host = self.get_proxy_host(host_id)
        has_ssl = current_host.get('certificate_id') and current_host['certificate_id'] > 0
        
        payload = {
            "domain_names": domain_names
        }
        
        # If the host has SSL and we should renew the certificate
        if has_ssl and renew_certificate:
            # Request a new certificate for the new domain name
            payload["certificate_id"] = "new"
            # Preserve the Let's Encrypt email from the host's meta or use the client's username
            letsencrypt_email = current_host.get('meta', {}).get('letsencrypt_email', self.username)
            payload["meta"] = {
                "letsencrypt_agree": True,
                "letsencrypt_email": letsencrypt_email,
                "dns_challenge": False
            }
        
        result = self._request('PUT', f'/nginx/proxy-hosts/{host_id}', json=payload)
        
        # If we renewed the certificate, re-apply SSL settings (same as create_proxy_host)
        if has_ssl and renew_certificate and result.get('certificate_id'):
            update_payload = {}
            
            if current_host.get('ssl_forced'):
                update_payload["ssl_forced"] = True
            if current_host.get('hsts_enabled'):
                update_payload["hsts_enabled"] = True
            if current_host.get('hsts_subdomains'):
                update_payload["hsts_subdomains"] = True
            if current_host.get('http2_support'):
                update_payload["http2_support"] = True
            
            if update_payload:
                result = self._request('PUT', f'/nginx/proxy-hosts/{host_id}', json=update_payload)
        
        return result
    
    def delete_proxy_host(self, host_id: int) -> bool:
        """
        Delete a proxy host.
        
        Args:
            host_id: The ID of the proxy host to delete
            
        Returns:
            True if successful
            
        Raises:
            APIError: If deletion fails
        """
        return self._request('DELETE', f'/nginx/proxy-hosts/{host_id}')
    
    def enable_proxy_host(self, host_id: int) -> Dict[str, Any]:
        """
        Enable a proxy host.
        
        Args:
            host_id: The ID of the proxy host to enable
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If enabling fails
        """
        return self.update_proxy_host(host_id, enabled=True)
    
    def disable_proxy_host(self, host_id: int) -> Dict[str, Any]:
        """
        Disable a proxy host.
        
        Args:
            host_id: The ID of the proxy host to disable
            
        Returns:
            Dict containing the updated proxy host details
            
        Raises:
            APIError: If disabling fails
        """
        return self.update_proxy_host(host_id, enabled=False)
    
    def close(self) -> None:
        """Close the HTTP session"""
        self._session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
