import frappe
import frappe.auth
import json
from frappe.utils import now
from frappe import _  # ✅ REQUIRED for frappe.throw to work
from ledgerctrl.ledgerctrl.api.jwt_auth import (
    generate_access_token,
    generate_refresh_token,
    verify_access_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_user_from_token
)

@frappe.whitelist(allow_guest=True)
def user_logn(usr, passwd, use_jwt=False, device_info=None):
    """
    Login endpoint with hybrid authentication support.

    Args:
        usr: Username or email
        passwd: Password
        use_jwt: If True, returns JWT tokens instead of api_key/secret
        device_info: Optional device information for refresh token tracking
    """
    try:
        login_mngr = frappe.auth.LoginManager()
        login_mngr.authenticate(user=usr, pwd=passwd)
        login_mngr.post_login()
    except frappe.exceptions.AuthenticationError as e:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": "Invalid login details. Please try again.",
            "timestamp": now()
        }
        return

    user = frappe.get_doc('User', frappe.session.user)
    user_data = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "roles": [r.role for r in user.get("roles")],
        "last_login": user.last_login,
        "mobile_no": user.mobile_no,
        "phone": user.phone,
        "language": user.language
    }

    frappe.local.response["sid"] = frappe.session.sid

    if use_jwt:
        # Generate JWT tokens
        access_token = generate_access_token(user_data)
        refresh_token = generate_refresh_token(user.email, device_info)

        frappe.local.response["message"] = {
            "success_key": 1,
            "message": "Login successful",
            "timestamp": now(),
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 900,  # 15 minutes in seconds
                **user_data
            }
        }
    else:
        # Legacy API key/secret approach
        api_secret = compose_api_key(frappe.session.user)

        frappe.local.response["message"] = {
            "success_key": 1,
            "message": "Login successful",
            "timestamp": now(),
            "data": {
                "api_key": user.api_key,
                "api_secret": api_secret,
                **user_data
            }
        }

def compose_api_key(user):
    user_doc = frappe.get_doc('User', user)
    api_secret = frappe.generate_hash(length=23)

    if not user_doc.api_key:
        user_doc.api_key = frappe.generate_hash(length=23)

    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)
    return api_secret


@frappe.whitelist( allow_guest=True)
def get_user_info():
    try:
        
        user = frappe.session.user
        

        if not user or user == "Guest":
            frappe.throw(_("Invalid or expired session. Please login again."), frappe.AuthenticationError)

        user_doc = frappe.get_doc("User", user)
        print("The user doc is", user_doc)
        
        

        return {
            "success_key": 1,
            "message": "User info fetched successfully.",
            "data": {
                "full_name": user_doc.full_name,
                "username": user_doc.username,
                "email": user_doc.email,
                "mobile_no": user_doc.mobile_no,
                "phone": user_doc.phone,
                "roles": [r.role for r in user_doc.roles],
                "enabled": user_doc.enabled,
                "last_login": user_doc.last_login,
                "language": user_doc.language,
                "profile_img": user_doc.user_image  # ✅ Include image URL here
                
            }
        }

    except frappe.AuthenticationError as ae:
        frappe.local.response.http_status_code = 401
        return {
            "success_key": 0,
            "message": f"Authentication failed: {str(ae)}"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "GetUserInfo Error")
        frappe.local.response.http_status_code = 500
        return {
            "success_key": 0,
            "message": f"Error: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
def update_user_info(first_name=None, middle_name=None, last_name=None, mobile_no=None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Login required")

    doc = frappe.get_doc("User", user)
    if first_name: doc.first_name = first_name
    if middle_name is not None: doc.middle_name = middle_name  # can be blank
    if last_name is not None: doc.last_name = last_name
    if mobile_no: doc.mobile_no = mobile_no

    doc.save(ignore_permissions=True)

    return {"success": True, "message": "Updated successfully"}


@frappe.whitelist(allow_guest=True)
def refresh_token(refresh_token_str, device_info=None):
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token_str: The refresh token
        device_info: Optional device information

    Returns:
        dict: New access token and refresh token
    """
    try:
        # Verify refresh token and get user email
        user_email = verify_refresh_token(refresh_token_str)

        # Get user data
        user = frappe.get_doc("User", user_email)
        user_data = {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": [r.role for r in user.get("roles")],
            "last_login": user.last_login,
            "mobile_no": user.mobile_no,
            "phone": user.phone,
            "language": user.language
        }

        # Generate new tokens
        new_access_token = generate_access_token(user_data)
        new_refresh_token = generate_refresh_token(user_email, device_info)

        # Revoke old refresh token
        revoke_refresh_token(refresh_token_str)

        return {
            "success_key": 1,
            "message": "Token refreshed successfully",
            "timestamp": now(),
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 900  # 15 minutes in seconds
            }
        }

    except frappe.AuthenticationError as e:
        frappe.local.response.http_status_code = 401
        return {
            "success_key": 0,
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Refresh Token Error")
        frappe.local.response.http_status_code = 500
        return {
            "success_key": 0,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist()
def logout(refresh_token_str=None, logout_all=False):
    """
    Logout endpoint to revoke refresh tokens.

    Args:
        refresh_token_str: The refresh token to revoke (optional if logout_all=True)
        logout_all: If True, revokes all refresh tokens for the user
    """
    try:
        user = frappe.session.user

        if not user or user == "Guest":
            frappe.throw(_("Invalid session"), frappe.AuthenticationError)

        if logout_all:
            # Revoke all tokens for the user (stored as User docname)
            revoke_all_user_tokens(user)
            return {
                "success_key": 1,
                "message": "Logged out from all devices successfully"
            }
        elif refresh_token_str:
            # Revoke specific token
            revoke_refresh_token(refresh_token_str)
            return {
                "success_key": 1,
                "message": "Logged out successfully"
            }
        else:
            return {
                "success_key": 1,
                "message": "Session ended"
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Logout Error")
        frappe.local.response.http_status_code = 500
        return {
            "success_key": 0,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist(allow_guest=True)
def verify_jwt_token(token):
    """
    Verify a JWT access token and return user information.

    Args:
        token: JWT access token

    Returns:
        dict: User information if token is valid
    """
    try:
        user_data = get_user_from_token(token)
        return {
            "success_key": 1,
            "message": "Token is valid",
            "data": user_data
        }
    except frappe.AuthenticationError as e:
        frappe.local.response.http_status_code = 401
        return {
            "success_key": 0,
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Token Verification Error")
        frappe.local.response.http_status_code = 500
        return {
            "success_key": 0,
            "message": f"Error: {str(e)}"
        }


@frappe.whitelist(allow_guest=True)
def get_csrf_token():
    """
    Return the CSRF token for the current session.

    The web command center runs inside an iframe on the same origin as the
    desk, so browsers send the desk session cookie along with API calls.
    Frappe enforces CSRF on POST requests for sessions that have a token;
    the SPA must echo it back in the X-Frappe-CSRF-Token header.
    """
    return frappe.sessions.get_csrf_token()


@frappe.whitelist(allow_guest=True)
def session_login(device_info=None):
    """
    SSO for the embedded web command center: when the browser already has an
    authenticated Frappe session (e.g. the user is logged into the desk),
    return JWT tokens for that user so the SPA skips the password prompt.

    Returns success_key=0 for guests; the caller should fall back to the
    normal login form.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"success_key": 0, "message": "No active session"}

    doc = frappe.get_doc("User", user)
    user_data = {
        "username": doc.username,
        "email": doc.email,
        "full_name": doc.full_name,
        "roles": [r.role for r in doc.get("roles")],
        "last_login": doc.last_login,
        "mobile_no": doc.mobile_no,
        "phone": doc.phone,
        "language": doc.language,
    }

    access_token = generate_access_token(user_data)
    refresh_token = generate_refresh_token(doc.email, device_info or "Web session SSO")

    return {
        "success_key": 1,
        "message": "Session login successful",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,
            **user_data,
        },
    }
