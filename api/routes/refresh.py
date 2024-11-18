from urllib import response
from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
import logging
import jwt
import os
import datetime

refresh_blueprint = Blueprint("refresh", __name__)
secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")

client = current_app.client
uri = current_app.uri

@refresh_blueprint.route('/refresh', methods=["POST"])
def refresh() -> Tuple[Response, int]:
    try:
        refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            return jsonify({"message": "No refresh token provided"}), status.UNAUTHORIZED

        decoded_refresh_token = jwt.decode(refresh_token, secret_key, algorithms=[auth_algorithm])
        userId = decoded_refresh_token["userId"]
        new_access_token = jwt.encode(
            {
                "userId": userId,
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
                "iat": datetime.datetime.now(datetime.timezone.utc),
                "role": decoded_refresh_token["role"],
            },
            secret_key,
            auth_algorithm
        )

        response = jsonify({
            "message": "Token refreshed",
        })

        response.set_cookie("access_token", value=new_access_token, httponly=True, domain='localhost', samesite='None', path='/', secure=True)
        return response, status.OK
    except jwt.InvalidTokenError:
        logging.error("Invalid refresh token.")
        return jsonify({"message": "Invalid refresh token"}), status.UNAUTHORIZED
    except Exception as e:
        logging.error(f"Error refreshing token: {e}")
        return jsonify({"message": "Error refreshing token"}), status.INTERNAL_SERVER_ERROR
