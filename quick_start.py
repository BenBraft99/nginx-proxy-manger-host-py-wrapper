"""
Quick start script for Nginx Proxy Manager Python Client

This is a minimal example to get you started quickly.
"""

from npm_client import NginxProxyManagerClient

# Configure your Nginx Proxy Manager instance
NPM_HOST = "http://ip"  # Change to your NPM instance URL
NPM_USERNAME = "admin@changeme"  # Change to your username
NPM_PASSWORD = "changeme"  # Change to your password


def quick_start():
    """Quick start example"""
    # Initialize client with debug mode
    client = NginxProxyManagerClient(
        host=NPM_HOST,
        username=NPM_USERNAME,
        password=NPM_PASSWORD,
        debug=True  # Enable debug output
    )
    
    # Optional: Clean up previous test hosts
    # try:
    #     client.delete_proxy_host(13)  # Replace with your test host ID
    #     print("🗑️  Cleaned up previous test host\n")
    # except:
    #     pass
    
    # Create a proxy host with SSL
    print("Creating proxy host with SSL...")
    host = client.create_proxy_host(
        domain_name="test.supabase.dev.flowwy.de",      # Your domain
        forward_host="192.168.1.100",       # Your backend server IP/hostname
        forward_port=8080,                   # Your backend server port
        letsencrypt_email=NPM_USERNAME,       # Email for Let's Encrypt notifications
        block_exploits=True,
        http2_support=True,
        ssl_forced=True,
        hsts_enabled=False,
        allow_websocket_upgrade=True
    )
    
    print(f"✅ Proxy host created!")
    print(f"   ID: {host['id']}")
    print(f"   Domain: {', '.join(host['domain_names'])}")
    print(f"   Forwarding to: {host['forward_host']}:{host['forward_port']}")
    print(f"   SSL Certificate: {'Yes' if host['certificate_id'] else 'No'}")
    print(f"   HTTPS forced: {host['ssl_forced']}")
    print(f"   HTTP/2 enabled: {host['http2_support']}")
    print(f"   Exploits blocked: {host['block_exploits']}")
    
    # Get the host ID for later operations
    host_id = host['id']
    
    # Rename the domain (optional)
    print("\nRenaming domain...")
    client.rename_proxy_host(host_id, "test2.supabase.dev.flowwy.de")
    print("✅ Domain renamed!")
    
    # Delete the proxy host (optional - comment out if you want to keep it)
    # print("\nDeleting proxy host...")
    # client.delete_proxy_host(host_id)
    # print("✅ Proxy host deleted!")
    
    client.close()


if __name__ == "__main__":
    quick_start()
