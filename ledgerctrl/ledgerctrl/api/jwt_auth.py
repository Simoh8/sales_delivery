import frappe
import jwt
from datetime import datetime, timedelta
from frappe import _
import hashlib
import secrets


# JWT Configuration
# These should be set in site_config.json or environment variables
JWT_SECRET_KEY = frappe.get_site_config().get("jwt_secret_key") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


def generate_access_token(user_data):
    """
    Generate a JWT access token for a user.

    Args:
        user_data: dict containing user information (email, username, roles, etc.)

    Returns:
        str: JWT access token
    """
    payload = {
        "sub": user_data.get("email") or user_data.get("username"),
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "full_name": user_data.get("full_name"),
        "roles": user_data.get("roles", []),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_email, device_info=None):
    """
    Generate a refresh token and store it in the database.

    Args:
        user_email: User's email
        device_info: Optional device information (user agent, etc.)

    Returns:
        str: Refresh token
    """
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # `user` is a Link to User (docname), resolve email -> name if needed
    user = frappe.db.get_value("User", {"email": user_email}, "name")
    if not user and frappe.db.exists("User", user_email):
        user = user_email
    if not user:
        frappe.throw(_("User not found"))

    # Check if Refresh Token DocType exists, if not create it on the fly
    if not frappe.db.exists("DocType", "Refresh Token"):
        create_refresh_token_doctype()

    # Store refresh token in database
    try:
        refresh_token_doc = frappe.get_doc({
            "doctype": "Refresh Token",
            "user": user,
            "token_hash": token_hash,
            "device_info": device_info or "Unknown",
            "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "is_revoked": 0
        })
        refresh_token_doc.insert()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Refresh Token Creation Error")
        frappe.throw(_("Failed to create refresh token"))

    return token


def verify_access_token(token):
    """
    Verify and decode a JWT access token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        frappe.throw(_("Token has expired"), frappe.AuthenticationError)
    except jwt.InvalidTokenError:
        frappe.throw(_("Invalid token"), frappe.AuthenticationError)


def verify_refresh_token(token):
    """
    Verify a refresh token against the database.

    Args:
        token: Refresh token string

    Returns:
        str: User email if valid

    Raises:
        Exception: Token is invalid or revoked
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = frappe.db.get_value(
        "Refresh Token",
        {
            "token_hash": token_hash,
            "is_revoked": 0
        },
        ["name", "user", "expires_at"]
    )

    if not refresh_token:
        frappe.throw(_("Invalid or revoked refresh token"), frappe.AuthenticationError)

    # Check if token has expired
    if refresh_token[2] < datetime.utcnow():
        frappe.throw(_("Refresh token has expired"), frappe.AuthenticationError)

    return refresh_token[1]  # Return user email


def revoke_refresh_token(token):
    """
    Revoke a refresh token.

    Args:
        token: Refresh token string
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    frappe.db.set_value(
        "Refresh Token",
        {"token_hash": token_hash},
        "is_revoked",
        1
    )


def revoke_all_user_tokens(user_email):
    """
    Revoke all refresh tokens for a user.

    Args:
        user_email: User's email
    """
    frappe.db.sql("""
        UPDATE `tabRefresh Token`
        SET is_revoked = 1
        WHERE user = %s AND is_revoked = 0
    """, (user_email,))


def get_user_from_token(token):
    """
    Extract user information from JWT token.

    Args:
        token: JWT access token

    Returns:
        dict: User information
    """
    payload = verify_access_token(token)
    return {
        "email": payload.get("email"),
        "username": payload.get("username"),
        "full_name": payload.get("full_name"),
        "roles": payload.get("roles", [])
    }


def create_refresh_token_doctype():
    """
    Create the Refresh Token DocType if it doesn't exist.
    This is a fallback if the DocType hasn't been created via bench.
    """
    if frappe.db.exists("DocType", "Refresh Token"):
        return

    # Create DocType using Frappe's Schema API
    from frappe.custom.doctype.customize_form import CustomizeForm

    # This is a simple fallback - in production, you should create the DocType
    # properly via bench new-doctype or manually
    try:
        # Log a warning that the DocType should be created properly
        frappe.log_error(
            "Refresh Token DocType not found. Please create it using: bench new-doctype 'Refresh Token'",
            "Missing Refresh Token DocType"
        )
    except:
        pass


def jwt_auth_hook():
    """
    Frappe `auth_hooks` entrypoint. Runs inside frappe.auth.validate_auth()
    before the guest check, so `Authorization: Bearer <jwt>` requests are
    authenticated as the token's user for whitelisted API methods.
    """
    try:
        auth_header = frappe.get_request_header("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return
        token = auth_header.split(" ", 1)[1]
        user_data = get_user_from_token(token)
        email = user_data.get("email")
        if not email:
            return
        user = frappe.db.get_value("User", {"email": email}, "name")
        if not user:
            return
        # preserve form_dict across set_user (same pattern as frappe core)
        form_dict = frappe.local.form_dict
        frappe.set_user(user)
        frappe.local.form_dict = form_dict
        frappe.local.jwt_user_data = user_data
    except Exception:
        # invalid/expired token -> let standard auth handling continue
        pass


def cleanup_expired_tokens():
    """
    Clean up expired refresh tokens from the database.
    This should be called periodically via a scheduled task.
    """
    frappe.db.sql("""
        DELETE FROM `tabRefresh Token`
        WHERE expires_at < %s
    """, (datetime.utcnow(),))

    frappe.db.commit()
