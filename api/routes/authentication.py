import logging
import os
from tokens import generate_tokens
from flask import Blueprint, Response, current_app, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from pydantic import ValidationError
from typing import Dict, Tuple
import http_status_codes as status
from models import LoginRequest, CreateNewUser, UserRole
from pymongo.errors import WriteError, OperationFailure

secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")
auth_blueprint = Blueprint("auth", __name__)

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_accounts_collection = current_app.config['DB_ACCOUNTS_COLLECTION']

@auth_blueprint.route('/auth/login', methods=['POST'])
def login() -> Tuple[Response, int]:
    try:
        login_request: LoginRequest = LoginRequest.model_validate_json(request.data)
        login_dict: Dict = login_request.model_dump()

        db = client[db_name]
        user = db[db_accounts_collection].find_one({"email": login_dict['email']})
        
        if not user or not check_password_hash(user['password'], login_dict['password']):
            return jsonify({"error": "Invalid email or password"}), status.UNAUTHORIZED

        access_token, refresh_token = generate_tokens(str(user['_id']), user['role'])
        
        response = jsonify({
            "message": "Logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token
        })
        response.set_cookie("access_token", access_token, httponly=True)
        response.set_cookie("refresh_token", refresh_token, httponly=True)

        return response, status.OK
    except ValidationError as e:
        logging.error("ValidationError: %s", e)
        return jsonify({"error": "Invalid input data"}), status.BAD_REQUEST

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while writing to the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"error": "Error logging in the user."}), status.INTERNAL_SERVER_ERROR

@auth_blueprint.route('/auth/register', methods=["POST"])
def register() -> Tuple[Response, int]:
    try:
        create_user_request: CreateNewUser = CreateNewUser.model_validate_json(request.data)
        create_user_dict: Dict = create_user_request.model_dump()
        
        create_user_dict['password'] = generate_password_hash(create_user_dict['password'], method='pbkdf2:sha256', salt_length=16)
        
        db = client[db_name]
        collection = db[db_accounts_collection]
        response = collection.insert_one(create_user_dict)
        if response.inserted_id is not None:
            return jsonify({"message": "User registered successfully"}), status.CREATED
        else:
            return jsonify({"error": "Registration failed"}), status.INTERNAL_SERVER_ERROR
    except ValidationError as e:
        return jsonify({'error': str(e)}), status.BAD_REQUEST

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while writing to the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"error": "Error creating user."}), status.INTERNAL_SERVER_ERROR
