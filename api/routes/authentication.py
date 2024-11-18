import logging
import os
from tokens import generate_tokens
from flask import Blueprint, Response, current_app, request, jsonify
from pydantic import ValidationError
from typing import Dict, Tuple
import http_status_codes as status
from emails import send_email_to_user
from bson.objectid import ObjectId
from models import LoginRequest, EmailRequest, ForgotPasswordRequest
from pymongo.errors import WriteError, OperationFailure
from passwords import generate_password, bcrypt_hash_password, bcrypt_verify_password
from middleware import is_token_valid, decode_token

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

        if not user or not bcrypt_verify_password(login_dict["password"], user['password']):
            return jsonify({"error": "Invalid email or password"}), status.UNAUTHORIZED

        try:
            access_token, refresh_token = generate_tokens(str(user['_id']), user['role'])
        except Exception as e:
            logging.error("Error generating tokens: %s", e)
            return jsonify({"error": "Error generating tokens"}), status.INTERNAL_SERVER_ERROR

        response = jsonify({
            "message": "Logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user['role']
        })
        print('Setting cookies', access_token, refresh_token)
        response.set_cookie("access_token", value=access_token, httponly=True, domain='localhost', samesite='None', path='/', secure=True)
        response.set_cookie("refresh_token", value=refresh_token, httponly=True, domain='localhost', samesite='None', path='/', secure=True)

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

@auth_blueprint.route('/auth/role', methods=['GET'])
def get_role()-> Tuple[Response, int]:
    if request.method != "GET":
        return jsonify({'error': 'Method is not supported.'}), status.METHOD_NOT_ALLOWED

    access_token = request.cookies.get("access_token")
    if not is_token_valid(access_token):
        return jsonify({'error':'The Access Token provided is invalid.'}), status.UNAUTHORIZED

    decoded_token = decode_token(access_token)
    role = decoded_token.get('role', None)

    if role == None:
        return jsonify({'error': 'Error getting role'}), status.INTERNAL_SERVER_ERROR

    return jsonify({'role':role}), status.OK

@auth_blueprint.route('/auth/forgot/password', methods=['POST'])
def forgot_password() -> Tuple[Response, int]:
    try:
        forgot_password_request: ForgotPasswordRequest = ForgotPasswordRequest.model_validate_json(request.data)
        forgot_password_dict: Dict = forgot_password_request.model_dump()
        db = client[db_name]
        existing_user =  db[db_accounts_collection].find_one({"email": forgot_password_dict['email']})
        if not existing_user:
            # Not returning an error to client here for security purposes
            logging.error("Email does not exist.")
            return jsonify({"content": "If this user exists, we have sent you a password reset email."}), status.OK

        email_account = existing_user["email"]
        new_password = generate_password()

        logging.info(f"Generated unsalted password for testing: {new_password}")

        new_hashed_password = bcrypt_hash_password(new_password)
        change_password_attempt = db[db_accounts_collection].update_one(
                {"_id": ObjectId(existing_user["_id"])},
                {"$set":{"password": new_hashed_password}}
                )

        if change_password_attempt.modified_count!=1:
            logging.error("MongoDB error while setting new generated password")
            return jsonify({"content": "If this user exists, we have sent you a password reset email."}), status.OK


        email_request = EmailRequest(
                email_account=email_account,
                subject="UA CTF Password Reset",
                message=f"""
        Dear User,

        Your password has been reset as requested. Here are your new login credentials:

        Email: {email_account}
        Password: {new_password}

        Best regards,
        The Team
                """.strip()
            )

        email_attempt_successful = send_email_to_user(email_request)
        if not email_attempt_successful:
            logging.error(f"Failed to send welcome email to {email_account}")
            return jsonify({"content": "If this user exists, we have sent you a password reset email."}), status.OK
        logging.info("Successfully reset password and sent to the user!")
        return jsonify({"content": "If this user exists, we have sent you a password reset email."}), status.OK

    except ValidationError as e:
        logging.error("ValidationError: %s", e)
        return jsonify({"error": "Forgot Password Request is not formatted properly."}), status.BAD_REQUEST

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'Experiencing internal server dependency error. Check server logs for details.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"error": "Internal Server Error."}), status.INTERNAL_SERVER_ERROR



@auth_blueprint.route('/auth/logout', methods=['POST'])
def logout() -> Tuple[Response, int]:
    try:
        access_token = request.cookies.get('access_token')
        refresh_token = request.cookies.get('refresh_token')

        if not access_token or not refresh_token:
            return jsonify({"error": "No active session found"}), status.BAD_REQUEST

        response = jsonify({"message": "Logged out successfully"})

        response.delete_cookie("access_token", domain='localhost', path='/', secure=True, samesite='None')
        response.delete_cookie("refresh_token", domain='localhost', path='/', secure=True, samesite='None')

        return response, status.OK
    except Exception as e:
        logging.error("Encountered exception while logging out: %s", e)
        return jsonify({"error": "Error logging out the user"}), status.INTERNAL_SERVER_ERROR
