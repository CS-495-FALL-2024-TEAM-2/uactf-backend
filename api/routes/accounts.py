import base64
import hashlib
import os
import logging
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request, Response
from typing import Dict, Tuple
from pydantic import ValidationError
from models import CreateTeacherRequest
import http_status_codes as status
import bcrypt

#TODO: Remove routes being public and Modify to work with middleware once it is complete

# Defining the blueprint
accounts_blueprint = Blueprint("accounts", __name__)
logging.basicConfig(level = logging.INFO)
# Get database configurations
client = current_app.client
uri: str = current_app.uri
db_name: str = current_app.config['DB_NAME']
db_accounts_collection: str = current_app.config['DB_ACCOUNTS_COLLECTION']
db_teacher_info_collection: str = current_app.config["DB_TEACHER_INFO_COLLECTION"]

# This is only for non-student accounts. I.e. Crimson-Defense Accounts, Teachers, Admins, Superadmins
def generate_password(length=12):
    password_bytes = os.urandom(length)
    password = base64.urlsafe_b64encode(password_bytes).decode('utf-8')[:length]
    return password

def bcrypt_hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')  # Return as a string

def bcrypt_verify_password(provided_password: str, stored_hashed_password: str) -> bool:
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hashed_password.encode('utf-8'))

@accounts_blueprint.route('/accounts/teachers/create', methods=["POST"])
def create_teacher_account() -> Tuple[Response, int]:
    try:
        # Validate and parse the incoming request data
        create_teacher_request: CreateTeacherRequest = CreateTeacherRequest.model_validate_json(request.data)
        create_teacher_dict: Dict = create_teacher_request.model_dump()
        create_teacher_dict['created_at'] = datetime.now()

        # Extract necessary information from the request data
        teacher_first_name = create_teacher_dict["first_name"]
        teacher_last_name  = create_teacher_dict["last_name"]
        teacher_user_name = teacher_first_name + "_" + teacher_last_name
        teacher_email = create_teacher_dict["email"]  # Assuming the email is passed in the request

        # Generate password and salt, then hash the password
        password = generate_password()
        hashed_password = bcrypt_hash_password(password)

        # Log the unsalted password for testing purposes
        logging.info(f"Generated unsalted password for testing: {password}")

        # Prepare account dictionary
        teacher_account_dict = {
            "competition_id": None,  # Assuming the competition ID is not provided in this route
            "email": teacher_email,
            "username": teacher_user_name,
            "password": hashed_password,  # Store the salted and hashed password
            "role": "teacher",
        }

        # Insert the account into the Accounts collection and get the new account's ID
        account_id = client[db_name][db_accounts_collection].insert_one(teacher_account_dict).inserted_id

        # Prepare teacher info dictionary
        teacher_info_dict = {
            "account_id": account_id,
            "first_name": teacher_first_name,
            "last_name": teacher_last_name,
            "created_at": create_teacher_dict['created_at'],
            "school_name": create_teacher_dict["school_name"],
            "school_address": create_teacher_dict["school_address"],
            "shirt_size": create_teacher_dict["shirt_size"],
        }

        # Insert the teacher info into the TeacherInfo collection
        client[db_name][db_teacher_info_collection].insert_one(teacher_info_dict)

        # Return success response
        return jsonify({"content": "Created account successfully!"}), status.CREATED

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"content": "Request does not have all parameters required or adhere to the schema."}), status.BAD_REQUEST

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"content": "Error creating account"}), status.INTERNAL_SERVER_ERROR

# This route is only to be able to test the account creation until the middleware is functional
@accounts_blueprint.route('/accounts/teachers/verify', methods=["GET"])
def verify_teacher_account() -> Tuple[Response, int]:
    try:
        # Get the username and password from the query parameters
        teacher_user_name = request.args.get("username")
        provided_password = request.args.get("password")

        if not teacher_user_name or not provided_password:
            return jsonify({"content": "Missing username or password in request"}), status.BAD_REQUEST

        # Fetch the teacher account from the Accounts collection using the username
        teacher_account = client[db_name][db_accounts_collection].find_one({"username": teacher_user_name})

        if not teacher_account:
            return jsonify({"content": "Teacher account not found"}), status.NOT_FOUND

        # Get the stored bcrypt-hashed password
        stored_hashed_password = teacher_account["password"]

        # Verify the provided password using bcrypt
        if bcrypt_verify_password(provided_password, stored_hashed_password):
            return jsonify({"content": "Verification successful!"}), status.OK
        else:
            return jsonify({"content": "Incorrect username or password"}), status.UNAUTHORIZED

    except Exception as e:
        logging.error(f"Unexpected error during verification: {e}")
        return jsonify({"content": "Error during verification"}), status.INTERNAL_SERVER_ERROR

