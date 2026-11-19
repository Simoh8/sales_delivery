import frappe
from functools import wraps
from frappe import _
from ledgerctrl.ledgerctrl.api.jwt_auth import verify_access_token, get_user_from_token


def jwt_required(f):
    """
    Decorator to require JWT authentication for an endpoint.

    Usage:
        @frappe.whitelist()
        @jwt_required
        def my_protected_endpoint():
            user = frappe.session.user
            # ... your code

    The decorator expects the JWT token in the Authorization header:
        Authorization: Bearer <token>

    Alternatively, it can be passed as a query parameter:
        ?token=<token>
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Try to get token from Authorization header
            auth_header = frappe.request.headers.get("Authorization")

            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            # Fallback to query parameter
            elif frappe.request.args.get("token"):
                token = frappe.request.args.get("token")
            else:
                frappe.local.response.http_status_code = 401
                return {
                    "success_key": 0,
                    "message": "Missing authentication token. Provide token in Authorization header or as ?token= parameter"
                }

            # Verify token
            user_data = get_user_from_token(token)

            # Set user in Frappe session context
            # This allows existing code that uses frappe.session.user to work
            user_email = user_data.get("email")
            user = frappe.db.get_value("User", {"email": user_email}, "name")

            if not user:
                frappe.local.response.http_status_code = 401
                return {
                    "success_key": 0,
                    "message": "User not found"
                }

            frappe.session.user = user
            frappe.local.session_user = user

            # Store user data in request for use in the endpoint
            frappe.local.jwt_user_data = user_data

            return f(*args, **kwargs)

        except frappe.AuthenticationError as e:
            frappe.local.response.http_status_code = 401
            return {
                "success_key": 0,
                "message": str(e)
            }
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "JWT Authentication Error")
            frappe.local.response.http_status_code = 500
            return {
                "success_key": 0,
                "message": f"Authentication error: {str(e)}"
            }

    return wrapper


def jwt_optional(f):
    """
    Decorator for optional JWT authentication.
    If token is provided, it validates and sets the user.
    If not provided, the endpoint still runs with Guest access.

    Usage:
        @frappe.whitelist(allow_guest=True)
        @jwt_optional
        def my_endpoint():
            if frappe.session.user != "Guest":
                # Authenticated user
            else:
                # Guest access
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Try to get token from Authorization header
            auth_header = frappe.request.headers.get("Authorization")

            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            elif frappe.request.args.get("token"):
                token = frappe.request.args.get("token")
            else:
                # No token provided, proceed as Guest
                return f(*args, **kwargs)

            # Verify token if provided
            user_data = get_user_from_token(token)

            # Set user in Frappe session context
            user_email = user_data.get("email")
            user = frappe.db.get_value("User", {"email": user_email}, "name")

            if user:
                frappe.session.user = user
                frappe.local.session_user = user
                frappe.local.jwt_user_data = user_data

            return f(*args, **kwargs)

        except frappe.AuthenticationError:
            # Invalid token, proceed as Guest
            return f(*args, **kwargs)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "JWT Optional Auth Error")
            # Proceed as Guest on error
            return f(*args, **kwargs)

    return wrapper


def role_required(*required_roles):
    """
    Decorator to require specific roles in addition to JWT authentication.

    Usage:
        @frappe.whitelist()
        @jwt_required
        @role_required("Driver", "Sales Person")
        def my_restricted_endpoint():
            # ... your code
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # First check if user is authenticated via JWT
            if not hasattr(frappe.local, 'jwt_user_data'):
                frappe.local.response.http_status_code = 401
                return {
                    "success_key": 0,
                    "message": "Authentication required"
                }

            user_roles = frappe.local.jwt_user_data.get("roles", [])

            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                frappe.local.response.http_status_code = 403
                return {
                    "success_key": 0,
                    "message": f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
                }

            return f(*args, **kwargs)

        return wrapper
    return decorator
