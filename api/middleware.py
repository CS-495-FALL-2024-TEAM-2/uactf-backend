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
    "/competitions/create",
    "/competitions/get",
    "/competitions/get/current",
    "/competitions/update/*"
]

protected_paths = {
    "/accounts/admin/create": ["admin"],
}


class Middleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            request = Request(environ)

            if any(request.path.startswith(path.replace('*', '')) for path in public_paths):
                return self.app(environ, start_response)

            access_token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")

            if request.path in protected_paths:
                allowed_roles = protected_paths[request.path]

                # Extract the access token from cookies
                access_token = request.cookies.get("access_token")

                # If no access token is present, return an Unauthorized response
                if not access_token:
                    response = Response("Unauthorized: No access token provided.", status=401)
                    return response(environ, start_response)

                # Validate access token
                token_valid = self.is_token_valid(access_token)
                if not token_valid:
                    response = Response("Unauthorized: Invalid or expired access token.", status=401)
                    return response(environ, start_response)

                token_data = self.decode_token(access_token)

                # Check if the user's role is authorized for this path
                user_role = token_data.get("role")
                if user_role not in allowed_roles:
                    response = Response(f"Forbidden: User role '{user_role}' is not allowed for this path.", status=403)
                    return response(environ, start_response)

                return self.app(environ, start_response)

            # Check for authorization
            if not access_token or not self.is_token_valid(access_token):
                if not refresh_token or not self.is_token_valid(refresh_token):
                    response = Response("Unauthorized", status=401)
                    return response(environ, start_response)

                new_access_token = self.refresh_access_token(refresh_token)
                response = ResponseStream()
                response.set_cookie("access_token", new_access_token, httponly=True)

            return self.app(environ, start_response)

        except Exception as e:
            logging.error(f"Error in Middleware: {e}")
            response = Response("Internal Server Error", status=500)
            return response(environ, start_response)

    def is_token_valid(self, token):
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

    def refresh_access_token(self, refresh_token):
        try:
            decoded_refresh_token = jwt.decode(refresh_token, secret_key, algorithms=[auth_algorithm])
            userId = decoded_refresh_token["userId"]

            new_access_token = generate_access_token(userId)
            
            return new_access_token
        except InvalidTokenError:
            logging.error("Invalid refresh token.")
            return None
    
    def decode_token(self, token):
        try:
            decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
            return decoded_token
        except Exception as e:
            logging.error(f"Error decoding token: {e}")
            return None
