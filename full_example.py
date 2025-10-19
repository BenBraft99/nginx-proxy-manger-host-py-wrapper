"""
Comprehensive example of using the Nginx Proxy Manager Python Client
"""

from npm_client import NginxProxyManagerClient, APIError, AuthenticationError

# ================================
# CONFIGURATION
# ================================
NPM_HOST = "http://your-server:81"     # Change this!
NPM_USERNAME = "admin@example.com"      # Change this!
NPM_PASSWORD = "changeme"                # Change this!


def main():
    """Demonstrate all major features of the client"""
    
    try:
        # Initialize the client
        print("🔐 Connecting to Nginx Proxy Manager...")
        client = NginxProxyManagerClient(
            host=NPM_HOST,
            username=NPM_USERNAME,
            password=NPM_PASSWORD
        )
        print("✅ Connected successfully!\n")
        
        # ================================
        # EXAMPLE 1: Create proxy WITHOUT SSL
        # ================================
        print("=" * 60)
        print("EXAMPLE 1: Creating proxy host WITHOUT SSL")
        print("=" * 60)
        
        host1 = client.create_proxy_host(
            domain_name="test1.example.com",
            forward_host="192.168.1.100",
            forward_port=8080,
            certificate_id=0,          # No SSL
            ssl_forced=False,
            hsts_enabled=False
        )
        
        print(f"✅ Created proxy host WITHOUT SSL")
        print(f"   ID: {host1['id']}")
        print(f"   Domain: {', '.join(host1['domain_names'])}")
        print(f"   Forwarding to: {host1['forward_host']}:{host1['forward_port']}")
        print(f"   SSL: No\n")
        
        host1_id = host1['id']
        
        # ================================
        # EXAMPLE 2: Get proxy host info
        # ================================
        print("=" * 60)
        print("EXAMPLE 2: Getting proxy host information")
        print("=" * 60)
        
        host_info = client.get_proxy_host(host1_id, expand=['certificate', 'owner'])
        print(f"✅ Retrieved proxy host info")
        print(f"   ID: {host_info['id']}")
        print(f"   Enabled: {host_info['enabled']}")
        print(f"   HTTP/2: {host_info['http2_support']}")
        print(f"   Block Exploits: {host_info['block_exploits']}\n")
        
        # ================================
        # EXAMPLE 3: Update proxy host settings
        # ================================
        print("=" * 60)
        print("EXAMPLE 3: Updating proxy host settings")
        print("=" * 60)
        
        updated_host = client.update_proxy_host(
            host_id=host1_id,
            forward_port=9000,              # Change port
            allow_websocket_upgrade=True,   # Enable WebSockets
            caching_enabled=True            # Enable caching
        )
        
        print(f"✅ Updated proxy host")
        print(f"   New forward port: {updated_host['forward_port']}")
        print(f"   WebSockets: {updated_host['allow_websocket_upgrade']}")
        print(f"   Caching: {updated_host['caching_enabled']}\n")
        
        # ================================
        # EXAMPLE 4: Rename proxy host
        # ================================
        print("=" * 60)
        print("EXAMPLE 4: Renaming proxy host")
        print("=" * 60)
        
        renamed_host = client.rename_proxy_host(
            host_id=host1_id,
            new_domain_name="renamed.example.com"
        )
        
        print(f"✅ Renamed proxy host")
        print(f"   New domain: {', '.join(renamed_host['domain_names'])}\n")
        
        # ================================
        # EXAMPLE 5: Create proxy WITH SSL
        # ================================
        print("=" * 60)
        print("EXAMPLE 5: Creating proxy host WITH SSL")
        print("=" * 60)
        print("⚠️  NOTE: This will only work if the domain points to your NPM server!")
        print("⚠️  For testing, we'll skip this. Change the domain to your own and uncomment.\n")
        
        # UNCOMMENT THESE LINES WHEN YOU HAVE A REAL DOMAIN:
        # host2 = client.create_proxy_host(
        #     domain_name="app.yourdomain.com",  # Must point to your NPM server!
        #     forward_host="192.168.1.100",
        #     forward_port=8080,
        #     # These are the defaults when certificate_id=None:
        #     certificate_id=None,               # Request new SSL cert
        #     ssl_forced=True,                   # Force HTTPS
        #     hsts_enabled=True,                 # Enable HSTS
        #     http2_support=True,                # Enable HTTP/2
        #     block_exploits=True,               # Block exploits
        #     letsencrypt_email="your@email.com"
        # )
        # print(f"✅ Created proxy host WITH SSL")
        # print(f"   ID: {host2['id']}")
        # print(f"   Domain: {', '.join(host2['domain_names'])}")
        # print(f"   SSL Certificate ID: {host2['certificate_id']}\n")
        # host2_id = host2['id']
        
        # ================================
        # EXAMPLE 6: List all proxy hosts
        # ================================
        print("=" * 60)
        print("EXAMPLE 6: Listing all proxy hosts")
        print("=" * 60)
        
        all_hosts = client.get_all_proxy_hosts()
        print(f"✅ Found {len(all_hosts)} proxy host(s):")
        for host in all_hosts:
            status = "🟢 Enabled" if host['enabled'] else "🔴 Disabled"
            ssl = f"🔒 SSL (ID: {host['certificate_id']})" if host['certificate_id'] else "🔓 No SSL"
            print(f"   [{host['id']}] {', '.join(host['domain_names'])} -> "
                  f"{host['forward_host']}:{host['forward_port']} | {status} | {ssl}")
        print()
        
        # ================================
        # EXAMPLE 7: Disable/Enable host
        # ================================
        print("=" * 60)
        print("EXAMPLE 7: Disabling and re-enabling proxy host")
        print("=" * 60)
        
        client.disable_proxy_host(host1_id)
        print(f"✅ Disabled proxy host {host1_id}")
        
        client.enable_proxy_host(host1_id)
        print(f"✅ Re-enabled proxy host {host1_id}\n")
        
        # ================================
        # EXAMPLE 8: Delete proxy host
        # ================================
        print("=" * 60)
        print("EXAMPLE 8: Deleting proxy host")
        print("=" * 60)
        
        # Ask for confirmation
        print(f"⚠️  About to delete proxy host {host1_id}")
        confirm = input("Type 'yes' to confirm deletion: ")
        
        if confirm.lower() == 'yes':
            client.delete_proxy_host(host1_id)
            print(f"✅ Deleted proxy host {host1_id}\n")
            
            # If we created host2, delete it too
            # if 'host2_id' in locals():
            #     client.delete_proxy_host(host2_id)
            #     print(f"✅ Deleted proxy host {host2_id}\n")
        else:
            print(f"⏭️  Skipped deletion\n")
        
        # Close the session
        client.close()
        print("=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Please check your username and password.")
    except APIError as e:
        print(f"❌ API Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Nginx Proxy Manager Python Client - Full Example")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Update NPM_HOST, NPM_USERNAME, and NPM_PASSWORD")
    print("at the top of this file before running!\n")
    
    main()
