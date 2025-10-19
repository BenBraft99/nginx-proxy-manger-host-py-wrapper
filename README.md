# Nginx Proxy Manager Python Client

A Python client library for interacting with the [Nginx Proxy Manager](https://nginxproxymanager.com/) API.

## Features

- ✅ **Easy Authentication** - Simple initialization with username/password
- ✅ **Automatic SSL Certificates** - Request Let's Encrypt certificates automatically
- ✅ **Proxy Host Management** - Create, update, rename, and delete proxy hosts
- ✅ **Security Features** - Enable HTTP/2, force HTTPS, block exploits, HSTS support
- ✅ **Type Hints** - Full type annotations for better IDE support
- ✅ **Error Handling** - Custom exceptions for better error management

## Installation

```bash
pip install -r requirements.txt
```

Or install the package:

```bash
pip install -e .
```

## Quick Start

```python
from npm_client import NginxProxyManagerClient

# Initialize the client
client = NginxProxyManagerClient(
    host="http://localhost:81",
    username="admin@example.com",
    password="changeme"
)

# Create a new proxy host with automatic SSL
host = client.create_proxy_host(
    domain_name="app.example.com",
    forward_host="192.168.1.100",
    forward_port=8080
)

print(f"Created proxy host with ID: {host['id']}")

# Rename the proxy host
client.rename_proxy_host(host['id'], "newapp.example.com")

# Delete the proxy host
client.delete_proxy_host(host['id'])
```

## Usage Examples

### Context Manager

```python
with NginxProxyManagerClient(
    host="http://localhost:81",
    username="admin@example.com",
    password="changeme"
) as client:
    # Create proxy host
    host = client.create_proxy_host(
        domain_name="app.example.com",
        forward_host="127.0.0.1",
        forward_port=3000
    )
```

### Create Proxy Host with Custom Options

```python
# Create a proxy host with custom settings
host = client.create_proxy_host(
    domain_name="api.example.com",
    forward_host="192.168.1.50",
    forward_port=8080,
    forward_scheme="https",  # Forward to HTTPS backend
    additional_domain_names=["api2.example.com"],  # Additional domains
    block_exploits=True,  # Block common exploits
    http2_support=True,  # Enable HTTP/2
    ssl_forced=True,  # Force HTTPS redirect
    hsts_enabled=True,  # Enable HSTS
    allow_websocket_upgrade=True,  # Allow WebSocket connections
    caching_enabled=False  # Disable caching
)
```

### List All Proxy Hosts

```python
# Get all proxy hosts
hosts = client.get_all_proxy_hosts(expand=["certificate", "owner"])

for host in hosts:
    print(f"ID: {host['id']}")
    print(f"Domains: {', '.join(host['domain_names'])}")
    print(f"Forward to: {host['forward_host']}:{host['forward_port']}")
    print("---")
```

### Update Proxy Host

```python
# Update specific fields
client.update_proxy_host(
    host_id=1,
    forward_port=9000,
    block_exploits=True,
    http2_support=True
)
```

### Rename Proxy Host

```python
# Change domain name(s)
client.rename_proxy_host(
    host_id=1,
    new_domain_name="newdomain.example.com",
    additional_domain_names=["www.newdomain.example.com"]
)
```

### Enable/Disable Proxy Host

```python
# Disable a proxy host
client.disable_proxy_host(host_id=1)

# Enable it again
client.enable_proxy_host(host_id=1)
```

### Manage Certificates

```python
# Get all certificates
certificates = client.get_certificates()

for cert in certificates:
    print(f"Certificate ID: {cert['id']}")
    print(f"Domains: {', '.join(cert['domain_names'])}")
    print(f"Expires: {cert['expires_on']}")
    print("---")

# Delete a certificate
client.delete_certificate(certificate_id=5)
```

## API Reference

### NginxProxyManagerClient

#### `__init__(host, username, password)`

Initialize the client and authenticate.

**Parameters:**
- `host` (str): Base URL of Nginx Proxy Manager (e.g., "http://localhost:81")
- `username` (str): Username/email for authentication
- `password` (str): Password for authentication

#### `create_proxy_host(...)`

Create a new proxy host with automatic SSL certificate.

**Parameters:**
- `domain_name` (str): Primary domain name
- `forward_host` (str): Target hostname/IP to forward requests to
- `forward_port` (int): Target port to forward requests to
- `forward_scheme` (str): Scheme for forwarding ("http" or "https"), default: "http"
- `additional_domain_names` (List[str], optional): Additional domain names
- `block_exploits` (bool): Enable blocking of common exploits, default: True
- `http2_support` (bool): Enable HTTP/2 support, default: True
- `ssl_forced` (bool): Force SSL (redirect HTTP to HTTPS), default: True
- `hsts_enabled` (bool): Enable HSTS, default: True
- `hsts_subdomains` (bool): Include subdomains in HSTS, default: False
- `allow_websocket_upgrade` (bool): Allow WebSocket connections, default: True
- `caching_enabled` (bool): Enable caching, default: False
- `access_list_id` (int): Access list ID (0 for none), default: 0
- `advanced_config` (str): Advanced Nginx configuration, default: ""
- `locations` (List[Dict], optional): Custom location blocks

**Returns:** Dict with created proxy host details

#### `get_proxy_host(host_id, expand=None)`

Get details of a specific proxy host.

**Returns:** Dict with proxy host details

#### `get_all_proxy_hosts(expand=None, query=None)`

Get all proxy hosts.

**Returns:** List of proxy host dictionaries

#### `update_proxy_host(host_id, **kwargs)`

Update an existing proxy host.

**Returns:** Dict with updated proxy host details

#### `rename_proxy_host(host_id, new_domain_name, additional_domain_names=None)`

Change the domain name(s) of a proxy host.

**Returns:** Dict with updated proxy host details

#### `delete_proxy_host(host_id)`

Delete a proxy host.

**Returns:** True if successful

#### `enable_proxy_host(host_id)`

Enable a proxy host.

**Returns:** True if successful

#### `disable_proxy_host(host_id)`

Disable a proxy host.

**Returns:** True if successful

#### `get_certificates()`

Get all SSL certificates.

**Returns:** List of certificate dictionaries

#### `delete_certificate(certificate_id)`

Delete an SSL certificate.

**Returns:** True if successful

## Error Handling

The library provides custom exceptions:

```python
from npm_client import (
    NginxProxyManagerError,  # Base exception
    AuthenticationError,      # Authentication failures
    APIError                  # API request failures
)

try:
    client = NginxProxyManagerClient(
        host="http://localhost:81",
        username="admin@example.com",
        password="wrong_password"
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e}")

try:
    host = client.create_proxy_host(
        domain_name="existing.example.com",
        forward_host="127.0.0.1",
        forward_port=8080
    )
except APIError as e:
    print(f"API error: {e}")
```

## Requirements

- Python 3.7+
- requests >= 2.31.0

## Default Settings

When creating a proxy host, the following defaults are applied:

- **HTTP/2 Support**: Enabled
- **Block Common Exploits**: Enabled
- **Force HTTPS**: Enabled (redirects HTTP to HTTPS)
- **HSTS**: Enabled
- **WebSocket Upgrade**: Enabled
- **SSL Certificate**: Automatically requested from Let's Encrypt
- **Caching**: Disabled

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
