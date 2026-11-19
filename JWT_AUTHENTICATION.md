# JWT Authentication Implementation

This document describes the hybrid JWT authentication system for the ledgerctrl app, which works with Frappe's existing authentication (email/password and API key/secret).

## Overview

The authentication system now supports two modes:

1. **Legacy Mode**: Uses Frappe's session-based authentication with API key/secret
2. **JWT Mode**: Uses JWT tokens for stateless mobile app authentication

Both modes can coexist, allowing gradual migration.

## Installation

### 1. Install Dependencies

The following dependencies have been added to `pyproject.toml`:
- `PyJWT>=2.8.0`
- `cryptography>=41.0.0`

Install them:
```bash
cd /home/simon/frappe-bench-v15
env/bin/pip install PyJWT cryptography
```

### 2. Configure JWT Secret

Add a JWT secret key to your site's configuration:

Edit `sites/[your-site]/site_config.json`:
```json
{
  "jwt_secret_key": "your-super-secret-jwt-key-here"
}
```

Generate a secure key:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Create Refresh Token DocType

The Refresh Token DocType has been created at:
`ledgerctrl/ledgerctrl/doctype/refresh_token/`

Run the migration:
```bash
bench migrate
```

## API Endpoints

### 1. Login (Hybrid)

**Endpoint**: `POST /api/method/ledgerctrl.ledgerctrl.api.login_api.user_logn`

**Parameters**:
- `usr`: Username or email
- `passwd`: Password
- `use_jwt`: (optional) Set to `true` to receive JWT tokens
- `device_info`: (optional) Device information for tracking

**Response (Legacy Mode)**:
```json
{
  "success_key": 1,
  "message": "Login successful",
  "data": {
    "api_key": "...",
    "api_secret": "...",
    "username": "...",
    "email": "...",
    "full_name": "...",
    "roles": [...]
  }
}
```

**Response (JWT Mode)**:
```json
{
  "success_key": 1,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "abc123xyz...",
    "token_type": "Bearer",
    "expires_in": 900,
    "username": "...",
    "email": "...",
    "full_name": "...",
    "roles": [...]
  }
}
```

### 2. Refresh Token

**Endpoint**: `POST /api/method/ledgerctrl.ledgerctrl.api.login_api.refresh_token`

**Parameters**:
- `refresh_token_str`: The refresh token
- `device_info`: (optional) Device information

**Response**:
```json
{
  "success_key": 1,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "new_abc123xyz...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

### 3. Logout

**Endpoint**: `POST /api/method/ledgerctrl.ledgerctrl.api.login_api.logout`

**Parameters**:
- `refresh_token_str`: (optional) The refresh token to revoke
- `logout_all`: (optional) Set to `true` to revoke all tokens for the user

**Response**:
```json
{
  "success_key": 1,
  "message": "Logged out successfully"
}
```

### 4. Verify Token

**Endpoint**: `POST /api/method/ledgerctrl.ledgerctrl.api.login_api.verify_jwt_token`

**Parameters**:
- `token`: JWT access token

**Response**:
```json
{
  "success_key": 1,
  "message": "Token is valid",
  "data": {
    "email": "...",
    "username": "...",
    "full_name": "...",
    "roles": [...]
  }
}
```

## Using JWT in Mobile Apps

### 1. Login Flow

```javascript
// Request
POST /api/method/ledgerctrl.ledgerctrl.api.login_api.user_logn
{
  "usr": "driver@example.com",
  "passwd": "password123",
  "use_jwt": true,
  "device_info": "iPhone 14, iOS 17.0"
}

// Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "abc123xyz...",
  "expires_in": 900
}

// Store tokens securely (e.g., Keychain/Keystore)
```

### 2. Making Authenticated Requests

```javascript
// Include the access token in Authorization header
GET /api/method/ledgerctrl.ledgerctrl.api.trips_api.get_assigned_orders
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 3. Token Refresh Flow

```javascript
// When access token expires (401 error)
POST /api/method/ledgerctrl.ledgerctrl.api.login_api.refresh_token
{
  "refresh_token_str": "abc123xyz..."
}

// Update stored tokens with new response
```

### 4. Logout Flow

```javascript
// Logout from current device
POST /api/method/ledgerctrl.ledgerctrl.api.login_api.logout
{
  "refresh_token_str": "abc123xyz..."
}

// Logout from all devices
POST /api/method/ledgerctrl.ledgerctrl.api.login_api.logout
{
  "logout_all": true
}
```

## Protecting Endpoints with JWT

### Using the @jwt_required Decorator

```python
from ledgerctrl.ledgerctrl.api.decorators import jwt_required

@frappe.whitelist()
@jwt_required
def my_protected_endpoint():
    user = frappe.session.user
    # Endpoint code here
```

### Using the @jwt_optional Decorator

```python
from ledgerctrl.ledgerctrl.api.decorators import jwt_optional

@frappe.whitelist(allow_guest=True)
@jwt_optional
def my_endpoint():
    if frappe.session.user != "Guest":
        # Authenticated user
    else:
        # Guest access
```

### Using the @role_required Decorator

```python
from ledgerctrl.ledgerctrl.api.decorators import jwt_required, role_required

@frappe.whitelist()
@jwt_required
@role_required("Driver", "Sales Person")
def my_restricted_endpoint():
    # Only accessible by users with Driver or Sales Person role
```

## Token Configuration

### Access Token
- **Expiration**: 15 minutes (configurable in `jwt_auth.py`)
- **Algorithm**: HS256
- **Contains**: User email, username, roles, full_name

### Refresh Token
- **Expiration**: 30 days (configurable in `jwt_auth.py`)
- **Storage**: Hashed in database (`Refresh Token` DocType)
- **Features**: Revocable, device tracking

## Security Best Practices

1. **Store JWT Secret Securely**: Never commit `jwt_secret_key` to version control
2. **Use HTTPS**: Always use HTTPS in production
3. **Secure Token Storage**: Store refresh tokens in secure storage (Keychain/Keystore)
4. **Token Rotation**: Refresh tokens are rotated on each refresh
5. **Logout on Token Theft**: Use `logout_all=true` if you suspect token theft
6. **Rate Limiting**: Implement rate limiting on login and refresh endpoints
7. **Monitor Failed Attempts**: Log and monitor failed authentication attempts

## Updated Endpoints

The following endpoints now support JWT authentication:

- `get_assigned_orders()` - Requires JWT
- `close_delivery_note_with_otp()` - Requires JWT
- `get_dashboard_stats()` - Optional JWT
- `get_recent_activity()` - Optional JWT
- `get_user_delivery_trips()` - Requires JWT

## Migration Guide

### For Existing Mobile Apps

1. Update login request to include `use_jwt: true`
2. Store both `access_token` and `refresh_token`
3. Include `Authorization: Bearer <token>` header in all requests
4. Implement token refresh logic on 401 errors
5. Update logout to call the new logout endpoint

### For Web Apps

Web apps can continue using the legacy session-based authentication. The JWT system is optional and both modes work side-by-side.

## Troubleshooting

### "Invalid token" Error
- Check that the token hasn't expired
- Verify the Authorization header format: `Bearer <token>`
- Ensure the JWT secret key is consistent across all servers

### "Refresh token has expired" Error
- User must log in again to get a new refresh token
- Check `REFRESH_TOKEN_EXPIRE_DAYS` configuration

### "Missing Refresh Token DocType" Error
- Run `bench migrate` to create the DocType
- Verify the DocType exists in the database

## Scheduled Tasks

Add to `hooks.py` to clean up expired tokens:

```python
scheduler_events = {
    "daily": [
        "ledgerctrl.ledgerctrl.api.jwt_auth.cleanup_expired_tokens"
    ]
}
```

## Support

For issues or questions, check:
- Error logs in Frappe: `Error Log` doctype
- Refresh Token records: `Refresh Token` doctype
- JWT configuration in `site_config.json`
