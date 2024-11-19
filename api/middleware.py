import os
from werkzeug.wrappers import Request, Response
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
    "/accounts/crimson_defense/create",
    "/accounts/teachers/create",
    "/competitions/get/current",
    "/auth/role",
    "/auth/forgot/password"
]

protected_paths = {
    "/auth/logout": ["admin", "crimson_defense", "teacher"],
    "/accounts/admin/create": ["admin"],
    "/challenges/create": ["crimson_defense", "admin"],
    "/competitions/create": ["admin"],
    "/competitions/<string:competition_id>": ["admin"],
    "/challenges/get": ["admin","crimson_defense"],
    "/competitions/get/current": ["teacher"],
    "/competitions/get": ["admin"],
    "/challenges/<string:challenge_id>" : ["admin", "crimson_defense"],
    "/teams/create": ["teacher", "admin"],
    "/teams/get": ["admin", "teacher"],
    "/teachers/get/all": ["admin"],
    "/teams/<string:team_id>": ["admin", "teacher"],
    "/reports/teams/info/create": ["admin"],
    "/teachers/upload-signed-liability-release-form": ["teacher"],
    "/admin/get-students-to-be-verified": ["admin"],
    "/admin/verify-student/<string:student_id>": ["admin"],
    "/reports/students/create": ["admin"],
}

def path_matches(pattern, path):
    if '*' in pattern:
        return path.startswith(pattern.rstrip('*'))
    else:
        return path == pattern

class Middleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            request = Request(environ)

            # Allow requests to public paths without authentication
            if any(path_matches(path, request.path) for path in public_paths) or request.method == "OPTIONS":
                return self.app(environ, start_response)

            access_token = request.cookies.get("access_token")
            refresh_token = request.cookies.get("refresh_token")


            # Check if the path requires specific role authorization
            for protected_path, allowed_roles in protected_paths.items():
                if path_matches(protected_path, request.path):
                    if not access_token:
                        response = Response("Unauthorized: No access token provided.", status=401)
                        return response(environ, start_response)

                    # Validate access token
                    if not is_token_valid(access_token):
                        response = Response("Unauthorized: Invalid or expired access token.", status=401)
                        return response(environ, start_response)

                    # Decode the token to get user role
                    token_data = decode_token(access_token)
                    user_role = token_data.get("role")

                    print("user_role,", user_role)

                    # Check if user role is authorized for the requested path
                    if user_role not in allowed_roles:
                        response = Response(
                            f"Forbidden: User role '{user_role}' is not allowed for this path.",
                            status=403
                        )
                        return response(environ, start_response)

                    # All checks passed, proceed with the request
                    return self.app(environ, start_response)

            # General token check for paths that require authentication but not specific roles
            if not access_token or not is_token_valid(access_token):
                if not refresh_token or not is_token_valid(refresh_token):
                    response = Response("Unauthorized", status=401)
                    return response(environ, start_response)

            # All checks passed, proceed with the request
            return self.app(environ, start_response)

        except Exception as e:
            logging.error(f"Error in Middleware: {e}")
            response = Response("Internal Server Error", status=500)
            return response(environ, start_response)

def is_token_valid(token):
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
        user_role = decoded_token.get("role", UserRole.teacher)
        if UserRole(user_role) not in UserRole:
            logging.error("Role is invalid or not recognized.")
            return False
        return True
    except ExpiredSignatureError:
        logging.error("Token has expired.")
        return False
    except InvalidTokenError:
        logging.error("Invalid token.")
        return False

def decode_token(token):
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
        return decoded_token
    except Exception as e:
        logging.error(f"Error decoding token: {e}")
        return None
