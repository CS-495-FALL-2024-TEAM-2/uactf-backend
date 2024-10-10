from werkzeug.wrappers import Request, Response, ResponseStream
import logging

public_paths = [
    "/",
    "/testdb",
    "/auth/login",
    "/accounts/teachers/create",
    "/accounts/teachers/verify"
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
        # TODO: Implement this function
        return True

    def refresh_access_token(self, refresh_token):
        # TODO: Implement this function
        return None
