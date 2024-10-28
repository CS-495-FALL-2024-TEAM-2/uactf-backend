import os
from werkzeug.wrappers import Request, Response, ResponseStream
import logging
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from models import UserRole
from tokens import generate_access_token

secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")

public_paths = [
    "/",
    "/testdb",
    "/auth/login",
    "/accounts/teachers/verify",
    "/accounts/admin/create",
    "/accounts/crimson_defense/create",
    "/accounts/teachers/create",
    "/competitions/get",
    "/competitions/get/current"
]

protected_paths = {
    "/challenges/create": ["crimson_defense", "admin"],
    "/competitions/create": ["admin"],
    "/competitions/update/*": ["admin"],
    "/challenges/get": ["admin"], 
    "/competitions/get/current": ["teacher"],
    }


class Middleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            request = Request(environ)

            # Allow requests to public paths without authentication
            if any(request.path.startswith(path.replace('*', '')) for path in public_paths):
                return self.app(environ, start_response)

            access_token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")

            # Check if the path requires specific role authorization
            for protected_path, allowed_roles in protected_paths.items():
                if request.path.startswith(protected_path.replace('*', '')):
                    # If no access token, return Unauthorized
                    if not access_token:
                        response = Response("Unauthorized: No access token provided.", status=401)
                        return response(environ, start_response)

                    # Validate access token
                    token_valid = is_token_valid(access_token)
                    if not token_valid:
                        response = Response("Unauthorized: Invalid or expired access token.", status=401)
                        return response(environ, start_response)

                    # Decode the token to get user role
                    token_data = decode_token(access_token)
                    user_role = token_data.get("role")

                    # Check if user role is authorized for the requested path
                    if user_role not in allowed_roles:
                        response = Response(f"Forbidden: User role '{user_role}' is not allowed for this path.", status=403)
                        return response(environ, start_response)

                    return self.app(environ, start_response)

            # General token check if the path does not require specific roles but still needs authentication. For endpoints that only requre login.
            if not access_token or not is_token_valid(access_token):
                # Check if refresh token is valid, otherwise return Unauthorized
                if not refresh_token or not is_token_valid(refresh_token):
                    response = Response("Unauthorized", status=401)
                    return response(environ, start_response)

                # Refresh access token using refresh token
                new_access_token = refresh_access_token(refresh_token)
                response = ResponseStream()
                response.set_cookie("access_token", new_access_token, httponly=True)

            return self.app(environ, start_response)

        except Exception as e:
            logging.error(f"Error in Middleware: {e}")
            response = Response("Internal Server Error", status=500)
            return response(environ, start_response)

def is_token_valid(token):
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
        
        user_role = decoded_token.get("role", UserRole.teacher)
        if user_role not in UserRole:
            logging.error("Role is invalid or not recognized.")
            return False

        return True
    except ExpiredSignatureError:
        logging.error("Token has expired.")
        return False
    except InvalidTokenError:
        logging.error("Invalid token.")
        return False

def refresh_access_token(refresh_token):
    try:
        decoded_refresh_token = jwt.decode(refresh_token, secret_key, algorithms=[auth_algorithm])
        userId = decoded_refresh_token["userId"]

        new_access_token = generate_access_token(userId)
        
        return new_access_token
    except InvalidTokenError:
        logging.error("Invalid refresh token.")
        return None

def decode_token(token):
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
        return decoded_token
    except Exception as e:
        logging.error(f"Error decoding token: {e}")
        return None

