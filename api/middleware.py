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
]

class Middleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            request = Request(environ)

            if request.path in public_paths:
                return self.app(environ, start_response)

            access_token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")

            # Check for authorization
            if not access_token or not self.is_token_valid(access_token):
                if not refresh_token or self.is_token_valid(refresh_token):
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
        