# SSL Settings Fix - Technical Documentation

## Problem

When creating a proxy host with `certificate_id: "new"` to request a new SSL certificate, the following settings were being ignored:
- `ssl_forced: true` → returned as `false`
- `http2_support: true` → returned as `false`
- `hsts_enabled: true` → returned as `false`
- `hsts_subdomains: true` → returned as `false`

Even though these values were sent correctly in the API payload, the backend was returning them as `false`.

## Root Cause

In the Nginx Proxy Manager backend (`backend/internal/host.js`), there's a function called `cleanSslHstsData()` that is called during proxy host creation. This function **clears SSL-related settings when no certificate is assigned yet**:

```javascript
// backend/lib/helpers.js or internal/host.js
cleanSslHstsData: (data) => {
    if (!data.certificate_id || data.certificate_id === 0) {
        data.ssl_forced = false;
        data.hsts_enabled = false;
        data.hsts_subdomains = false;
        data.http2_support = false;
    }
    return data;
}
```

During the creation flow with `certificate_id: "new"`:

1. The backend receives the proxy host creation request
2. It deletes `certificate_id: "new"` from the data (sets it to undefined/null)
3. It calls `cleanSslHstsData()` which sees no certificate ID and **clears all SSL settings**
4. The proxy host is created in the database without SSL settings
5. Then the SSL certificate is requested and created
6. The proxy host is updated with the `certificate_id`
7. But the SSL settings remain `false` because they were cleared earlier

## Solution

The fix is implemented in the Python client's `create_proxy_host()` method. After successfully creating a proxy host with a new certificate, we **make a second API call** to update the SSL settings:

```python
# Create the proxy host (SSL settings will be cleared by backend)
result = self._request('POST', '/nginx/proxy-hosts', json=payload)

# If a certificate was created, update to enable SSL settings
if request_new_cert and result.get('certificate_id'):
    update_payload = {}
    
    if ssl_forced:
        update_payload["ssl_forced"] = True
    if hsts_enabled:
        update_payload["hsts_enabled"] = True
        if hsts_subdomains:
            update_payload["hsts_subdomains"] = True
    if http2_support:
        update_payload["http2_support"] = True
    
    # Update the proxy host with SSL settings
    if update_payload:
        result = self._request('PUT', f'/nginx/proxy-hosts/{result["id"]}', json=update_payload)
```

## Flow

### Before Fix:
```
POST /nginx/proxy-hosts
├─ certificate_id: "new" 
├─ ssl_forced: true
├─ http2_support: true
└─ hsts_enabled: true
          ↓
Backend clears SSL settings (no cert yet)
          ↓
Creates proxy host with ssl_forced: false, etc.
          ↓
Creates SSL certificate
          ↓
Updates proxy host with certificate_id
          ↓
RESULT: Certificate exists, but SSL settings are false ❌
```

### After Fix:
```
POST /nginx/proxy-hosts
├─ certificate_id: "new"
├─ ssl_forced: true
├─ http2_support: true
└─ hsts_enabled: true
          ↓
Backend clears SSL settings (no cert yet)
          ↓
Creates proxy host with ssl_forced: false, etc.
          ↓
Creates SSL certificate
          ↓
Updates proxy host with certificate_id
          ↓
Returns to Python client
          ↓
Python client checks: certificate_id exists?
          ↓
YES → Make UPDATE request
          ↓
PUT /nginx/proxy-hosts/{id}
├─ ssl_forced: true
├─ http2_support: true
└─ hsts_enabled: true
          ↓
RESULT: Certificate exists AND SSL settings enabled ✅
```

## Testing

Before the fix:
```python
host = client.create_proxy_host(
    domain_name="test.example.com",
    forward_host="localhost",
    forward_port=8080,
    ssl_forced=True,        # Sent as true
    http2_support=True,     # Sent as true
    hsts_enabled=True       # Sent as true
)

print(host['ssl_forced'])      # false ❌
print(host['http2_support'])   # false ❌
print(host['hsts_enabled'])    # false ❌
```

After the fix:
```python
host = client.create_proxy_host(
    domain_name="test.example.com",
    forward_host="localhost",
    forward_port=8080,
    ssl_forced=True,        # Sent as true
    http2_support=True,     # Sent as true
    hsts_enabled=True       # Sent as true
)

print(host['ssl_forced'])      # true ✅
print(host['http2_support'])   # true ✅
print(host['hsts_enabled'])    # true ✅
```

## API Calls

The client now makes **2 API calls** when creating a proxy host with automatic SSL:

1. **POST** `/api/nginx/proxy-hosts` - Create host and request certificate
2. **PUT** `/api/nginx/proxy-hosts/{id}` - Enable SSL settings after certificate is created

This is necessary because of how the backend handles certificate creation and SSL settings validation.

## Performance Impact

- Minimal - The second API call is very fast (just updating boolean flags)
- Only happens when `certificate_id=None` (requesting new SSL)
- Does not happen when `certificate_id=0` (no SSL) or `certificate_id=<number>` (existing cert)

## Alternative Solutions Considered

### 1. Wait and retry (rejected)
```python
# Wait for cert, then update
time.sleep(10)
client.update_proxy_host(host_id, ssl_forced=True, ...)
```
**Problem**: Unreliable timing, may still fail

### 2. Check certificate status in loop (rejected)
```python
while not host.get('certificate_id'):
    time.sleep(1)
    host = client.get_proxy_host(host_id)
```
**Problem**: Unnecessary polling, the creation already waits for the cert

### 3. Current solution: Immediate update (chosen) ✅
```python
result = create_host()
if result.get('certificate_id'):
    result = update_settings(result['id'])
```
**Benefits**: 
- Reliable
- No waiting
- No polling
- Minimal overhead

## Backend Improvement Suggestion

The Nginx Proxy Manager backend could be improved to handle this better:

```javascript
// After certificate creation, re-apply SSL settings from original request
if (create_certificate && original_data.ssl_forced) {
    return internalProxyHost.update(access, {
        id: row.id,
        certificate_id: cert.id,
        ssl_forced: original_data.ssl_forced,
        hsts_enabled: original_data.hsts_enabled,
        hsts_subdomains: original_data.hsts_subdomains,
        http2_support: original_data.http2_support
    });
}
```

This would eliminate the need for the second API call from clients.

## Conclusion

The fix ensures that SSL-related settings are properly enabled when creating a proxy host with automatic SSL certificate generation. The solution is elegant, reliable, and adds minimal overhead.

---

**Fixed in**: npm_client.py `create_proxy_host()` method  
**Date**: October 19, 2025  
**Status**: ✅ Resolved
