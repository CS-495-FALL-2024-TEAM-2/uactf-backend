from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
import logging

refresh_blueprint = Blueprint("refresh", __name__)

client = current_app.client
uri = current_app.uri

@refresh_blueprint.route('/refresh', methods=["POST"])
def refresh() -> Tuple[Response, int]:
    # TODO: Implement this function
    return jsonify({"message": "Not implemented"}), status.NOT_IMPLEMENTED
