# Nginx Proxy Manager Python Client

A Python client library for interacting with the Nginx Proxy Manager API. This library makes it easy to automate the management of proxy hosts with automatic SSL certificate generation via Let's Encrypt.

## Features

- ✅ **Easy authentication** - Automatic JWT token management
- ✅ **Create proxy hosts** - With or without SSL certificates
- ✅ **Auto SSL** - Request new Let's Encrypt certificates automatically
- ✅ **Rename/Update hosts** - Change domain names and settings
- ✅ **Delete hosts** - Remove proxy hosts
- ✅ **Full configuration** - HTTP/2, HSTS, exploit blocking, WebSockets, and more
- ✅ **Error handling** - Detailed error messages for troubleshooting

## Installation

1. Make sure you have Python 3.7+ installed

2. Install required dependencies:
```bash
pip install requests
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

## Quick Start

```python
from npm_client import NginxProxyManagerClient

# Initialize the client
client = NginxProxyManagerClient(
    host="http://your-npm-server:81",
    username="admin@example.com",
    password="your-password"
)

# Create a proxy host WITH automatic SSL certificate
host = client.create_proxy_host(
    domain_name="app.yourdomain.com",
    forward_host="192.168.1.100",
    forward_port=8080
)

print(f"Created host with ID: {host['id']}")

# Rename a proxy host
client.rename_proxy_host(host['id'], "newapp.yourdomain.com")

# Delete a proxy host
client.delete_proxy_host(host['id'])

# Close the session
client.close()
```

## Usage Examples

### Creating a Proxy Host WITHOUT SSL

If you don't want SSL or want to add it later:

```python
host = client.create_proxy_host(
    domain_name="app.example.com",
    forward_host="localhost",
    forward_port=3000,
    certificate_id=0,          # 0 = no SSL
    ssl_forced=False,          # Don't redirect to HTTPS
    hsts_enabled=False         # Don't enable HSTS
)
```

### Creating a Proxy Host WITH SSL (Automatic Let's Encrypt)

**Important**: The domain must point to your Nginx Proxy Manager server for Let's Encrypt validation to work!

```python
host = client.create_proxy_host(
    domain_name="app.yourdomain.com",  # Must point to NPM server
    forward_host="192.168.1.100",
    forward_port=8080,
    # SSL settings (these are the defaults)
    certificate_id=None,               # None = request new SSL cert
    ssl_forced=True,                   # Force HTTPS redirect
    hsts_enabled=True,                 # Enable HSTS
    http2_support=True,                # Enable HTTP/2
    block_exploits=True,               # Block common exploits
    letsencrypt_email="your@email.com" # Email for Let's Encrypt notifications
)
```

### Renaming a Proxy Host

Change the domain name of an existing proxy host:

```python
# Simple rename (automatically renews SSL certificate if one exists)
client.rename_proxy_host(host_id=1, new_domain_name="newapp.yourdomain.com")

# With additional domains
client.rename_proxy_host(
    host_id=1,
    new_domain_name="app.yourdomain.com",
    additional_domain_names=["www.app.yourdomain.com", "api.yourdomain.com"]
)

# Rename WITHOUT renewing SSL certificate (not recommended if domain changes)
client.rename_proxy_host(
    host_id=1,
    new_domain_name="newapp.yourdomain.com",
    renew_certificate=False  # Keep old certificate (will cause SSL errors!)
)
```

**⚠️ IMPORTANT**: When you rename a proxy host that has an SSL certificate, the certificate needs to be renewed because SSL certificates are domain-specific. By default, `rename_proxy_host()` automatically requests a new SSL certificate for the new domain name. If you set `renew_certificate=False`, the old certificate will remain, which will cause SSL errors because the certificate won't match the new domain.

### Updating Other Settings

Update various settings of an existing proxy host:

```python
client.update_proxy_host(
    host_id=1,
    forward_host="192.168.1.200",  # Change backend server
    forward_port=9000,              # Change backend port
    block_exploits=True,            # Enable exploit blocking
    allow_websocket_upgrade=True    # Enable WebSockets
)
```

### Getting Proxy Host Information

```python
# Get a specific host
host = client.get_proxy_host(host_id=1, expand=['certificate', 'owner'])
print(f"Domain: {host['domain_names']}")
print(f"Forwarding to: {host['forward_host']}:{host['forward_port']}")

# Get all proxy hosts
all_hosts = client.get_all_proxy_hosts()
for host in all_hosts:
    print(f"ID: {host['id']}, Domain: {host['domain_names']}")
```

### Enable/Disable a Host

```python
# Disable a host (keeps configuration but stops proxying)
client.disable_proxy_host(host_id=1)

# Re-enable it
client.enable_proxy_host(host_id=1)
```

### Using Context Manager

The client supports Python's context manager protocol:

```python
with NginxProxyManagerClient(host="http://localhost:81", 
                              username="admin@example.com", 
                              password="changeme") as client:
    host = client.create_proxy_host(
        domain_name="app.example.com",
        forward_host="localhost",
        forward_port=8080
    )
    # Client automatically closes when exiting the with block
```

## Function Reference

### `NginxProxyManagerClient(host, username, password)`

Initialize the client with your NPM server details.

**Parameters:**
- `host` (str): Base URL of NPM instance (e.g., "http://localhost:81")
- `username` (str): Username/email for authentication
- `password` (str): Password

### `create_proxy_host(...)`

Create a new proxy host.

**Parameters:**
- `domain_name` (str): Primary domain name
- `forward_host` (str): Backend server hostname/IP
- `forward_port` (int): Backend server port
- `forward_scheme` (str): "http" or "https" (default: "http")
- `additional_domain_names` (List[str], optional): Additional domains
- `block_exploits` (bool): Block common exploits (default: True)
- `http2_support` (bool): Enable HTTP/2 (default: True)
- `ssl_forced` (bool): Force HTTPS redirect (default: True)
- `hsts_enabled` (bool): Enable HSTS (default: True)
- `hsts_subdomains` (bool): Include subdomains in HSTS (default: False)
- `allow_websocket_upgrade` (bool): Allow WebSocket connections (default: True)
- `caching_enabled` (bool): Enable caching (default: False)
- `access_list_id` (int): Access list ID (default: 0)
- `advanced_config` (str): Custom Nginx configuration
- `locations` (List[Dict], optional): Custom location blocks
- `certificate_id` (int, optional): Use existing certificate (0 = no SSL, None = request new)
- `letsencrypt_email` (str, optional): Email for Let's Encrypt (defaults to username)

**Returns:** Dict with created proxy host details

### `rename_proxy_host(host_id, new_domain_name, additional_domain_names=None)`

Rename a proxy host (change domain name).

**Parameters:**
- `host_id` (int): ID of the proxy host
- `new_domain_name` (str): New primary domain name
- `additional_domain_names` (List[str], optional): Additional domains

**Returns:** Dict with updated proxy host details

### `update_proxy_host(host_id, ...)`

Update an existing proxy host. Only provide parameters you want to change.

**Parameters:** Same as `create_proxy_host`, plus:
- `enabled` (bool, optional): Enable/disable the host

**Returns:** Dict with updated proxy host details

### `delete_proxy_host(host_id)`

Delete a proxy host.

**Parameters:**
- `host_id` (int): ID of the proxy host to delete

**Returns:** True if successful

### `get_proxy_host(host_id, expand=None)`

Get details of a specific proxy host.

**Parameters:**
- `host_id` (int): ID of the proxy host
- `expand` (List[str], optional): Related objects to expand (e.g., ['certificate', 'owner'])

**Returns:** Dict with proxy host details

### `get_all_proxy_hosts(expand=None)`

Get all proxy hosts.

**Parameters:**
- `expand` (List[str], optional): Related objects to expand

**Returns:** List of proxy host dictionaries

### `enable_proxy_host(host_id)` / `disable_proxy_host(host_id)`

Enable or disable a proxy host.

**Parameters:**
- `host_id` (int): ID of the proxy host

**Returns:** Dict with updated proxy host details

## Debugging

Enable debug mode to see detailed API requests and responses:

```python
client = NginxProxyManagerClient(
    host="http://localhost:81",
    username="admin@example.com",
    password="your-password",
    debug=True  # Enable debug output
)

# Now all API requests will show:
# - Request method and URL
# - Request payload
# - Response status code
# - Response body
```

This is very helpful when troubleshooting SSL certificate issues or other API errors.

## Troubleshooting SSL Issues

For comprehensive SSL troubleshooting, see:
- `SSL_TROUBLESHOOTING.md` - Common SSL errors and solutions
- `SSL_SOLUTION.md` - Detailed explanation of SSL certificate workflow
- `SSL_SETTINGS_FIX.md` - Information about SSL settings behavior

Common issues:
1. **500 Internal Server Error**: Often caused by Let's Encrypt rate limits. Use `reuse_certificate=True` to avoid this.
2. **SSL Certificate not created**: Domain must point to NPM server and port 80 must be accessible.
3. **SSL forced/HTTP/2 not enabled after creation**: This is normal NPM behavior. The client automatically updates these settings after certificate creation.

## Error Handling

The library raises two types of exceptions:

- `AuthenticationError`: When authentication fails
- `APIError`: When an API request fails

```python
from npm_client import NginxProxyManagerClient, APIError, AuthenticationError

try:
    client = NginxProxyManagerClient(
        host="http://localhost:81",
        username="admin@example.com",
        password="wrong-password"
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e}")

try:
    host = client.create_proxy_host(
        domain_name="app.example.com",
        forward_host="localhost",
        forward_port=8080
    )
except APIError as e:
    print(f"Failed to create proxy host: {e}")
```

## Important Notes

### SSL Certificate Requirements

For automatic Let's Encrypt SSL certificates to work:

1. **Your domain must point to the Nginx Proxy Manager server** via DNS A record
2. **Port 80 must be accessible** from the internet (Let's Encrypt needs to verify domain ownership)
3. **The domain must not already be in use** by another proxy host

If you're testing or the domain doesn't point to your server yet, create the proxy host WITHOUT SSL first:

```python
host = client.create_proxy_host(
    domain_name="app.example.com",
    forward_host="localhost",
    forward_port=8080,
    certificate_id=0,     # No SSL for now
    ssl_forced=False,
    hsts_enabled=False
)
```

Then later, when the domain is properly configured, you can update it to request SSL:

```python
client.update_proxy_host(
    host_id=host['id'],
    certificate_id="new",  # Request new SSL certificate
    ssl_forced=True,
    hsts_enabled=True
)
```

### Default Settings

When creating a proxy host with SSL, these defaults are applied:
- `http2_support=True` - HTTP/2 enabled
- `block_exploits=True` - Common exploit blocking enabled
- `ssl_forced=True` - HTTPS redirect enabled
- `hsts_enabled=True` - HSTS enabled
- `allow_websocket_upgrade=True` - WebSocket support enabled

### Avoiding Let's Encrypt Rate Limits

Let's Encrypt has rate limits (50 certificates per registered domain per week). To avoid hitting these limits when creating or renaming hosts, you can reuse existing certificates:

```python
# When creating a new host, check for existing certificates first
host = client.create_proxy_host(
    domain_name="app.yourdomain.com",
    forward_host="192.168.1.100",
    forward_port=8080,
    reuse_certificate=True,  # Check for existing cert before requesting new one
    letsencrypt_email="your@email.com"
)

# When renaming, also check for existing certificates
client.rename_proxy_host(
    host_id=1,
    new_domain_name="newapp.yourdomain.com",
    renew_certificate=True,   # Request new certificate
    reuse_certificate=True    # But check for existing cert first
)
```

**How it works**:
- When `reuse_certificate=True`, the client checks if a certificate already exists for the domain(s)
- If found, it reuses the existing certificate instead of requesting a new one
- If not found, it requests a new certificate from Let's Encrypt
- This is especially useful when:
  - Re-creating a host that was deleted
  - Testing and recreating hosts multiple times
  - Managing multiple hosts with the same domain

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
