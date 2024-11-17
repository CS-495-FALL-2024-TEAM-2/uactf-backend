import logging
from datetime import datetime
from os import stat
from flask import Blueprint, current_app, jsonify, request, Response
from typing import Dict, Tuple
from pydantic import ValidationError
from models import CreateAdminRequest, CreateCrimsonDefenseRequest, CreateTeacherRequest, EmailRequest
import http_status_codes as status
from bson.objectid import ObjectId
from passwords import generate_password, bcrypt_hash_password, bcrypt_verify_password
from emails import send_email_to_user

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

# TEACHER ACCOUNTS --------------------------------------------------------------
@accounts_blueprint.route('/accounts/teachers/create', methods=["POST"])
def create_teacher_account() -> Tuple[Response, int]:
    try:
        # Validate and parse the incoming request data
        create_teacher_request: CreateTeacherRequest = CreateTeacherRequest.model_validate_json(request.data)
        create_teacher_dict: Dict = create_teacher_request.model_dump()
        create_teacher_dict['created_at'] = datetime.now()

        # Extract necessary information from the request data
        teacher_email = create_teacher_dict["email"]  # Assuming the email is passed in the request
        teacher_first_name: str = create_teacher_dict["first_name"]
        teacher_last_name: str = create_teacher_dict["last_name"]

        email_exists =  client[db_name][db_accounts_collection].find_one({"email":teacher_email})
        if email_exists:
            logging.error("The user's email is already in the database.")
            return jsonify({"error": "Eror Creating Accout. Check Server Logs."}), status.UNAUTHORIZED

        # Generate password and salt, then hash the password
        password = generate_password()
        hashed_password = bcrypt_hash_password(password)

        # Log the unsalted password for testing purposes
        logging.info(f"Generated unsalted password for testing: {password}")

        email_request = EmailRequest(
                email_account=teacher_email,
                subject="UA CTF Account Details",
                message=f"""
        Dear {teacher_first_name} {teacher_last_name},

        Your account has been successfully created. Here are your login credentials:

        Email: {teacher_email}
        Password: {password}

        Best regards,
        The Team
                """.strip()
            )

        email_attempt_successful = send_email_to_user(email_request)
        if not email_attempt_successful:
            logging.error(f"Failed to send welcome email to {teacher_email}")
            return jsonify({"error": "Could not send email to the teacher"}), status.INTERNAL_SERVER_ERROR

        teacher_account_dict = {
            "competition_id": None,  # Assuming the competition ID is not provided in this route
            "email": teacher_email,
            "password": hashed_password,  # Store the salted and hashed password
            "role": "teacher",
        }

        # Insert the account into the Accounts collection and get the new account's ID
        account_id = client[db_name][db_accounts_collection].insert_one(teacher_account_dict).inserted_id

        if account_id is None:
            return jsonify({"content": "Could not find teacher in the database."}), status.NOT_FOUND

        # Prepare teacher info dictionary
        teacher_info_dict = {
            "account_id": account_id,
            "first_name": teacher_first_name,
            "last_name": teacher_last_name,
            "email": teacher_email,
            "created_at": create_teacher_dict['created_at'],
            "school_name": create_teacher_dict["school_name"],
            "school_address": create_teacher_dict["school_address"],
            "school_website": create_teacher_dict["school_website"],
            "contact_number": create_teacher_dict["contact_number"],
            "shirt_size": create_teacher_dict["shirt_size"],
        }

        # Insert the teacher info into the TeacherInfo collection
        client[db_name][db_teacher_info_collection].insert_one(teacher_info_dict)


        # Return success response
        return jsonify({
            "content": "Created account successfully!",
            "id": str(account_id),
            "role":"teacher",
            "first_name": teacher_first_name,
            "last_name": teacher_last_name
            }), status.CREATED

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
        teacher_email = request.args.get("email")
        provided_password = request.args.get("password")

        if not teacher_email or not provided_password:
            return jsonify({"content": "Missing email or password in request"}), status.BAD_REQUEST

        # Fetch the teacher account from the Accounts collection using the username
        teacher_account = client[db_name][db_accounts_collection].find_one({"email": teacher_email})

        if not teacher_account:
            return jsonify({"content": "Teacher account not found"}), status.NOT_FOUND

        teacher_info = client[db_name][db_teacher_info_collection].find_one({"account_id":ObjectId(teacher_account["_id"])})

        if teacher_info is None:
            return jsonify({"content": "Could not find teacher in the database."}), status.NOT_FOUND

        # Get the stored bcrypt-hashed password
        stored_hashed_password = teacher_account["password"]
        # Verify the provided password usiing bcrypt
        if bcrypt_verify_password(provided_password, stored_hashed_password):
            return jsonify({
                "content": "Verification successful!",
                "role": teacher_account["role"],
                "first_name": teacher_info["first_name"],
                "last_name": teacher_info["last_name"]
                }), status.OK
        else:
            return jsonify({"content": "Incorrect username or password"}), status.UNAUTHORIZED

    except Exception as e:
        logging.error(f"Unexpected error during verification: {e}")
        return jsonify({"content": "Error during verification"}), status.INTERNAL_SERVER_ERROR

# CRIMSON DEFENSE ACCOUNTS ----------------------------------------------------
@accounts_blueprint.route('/accounts/crimson_defense/create', methods=["POST"])
def create_crimson_defense_account() -> Tuple[Response, int]:
    try:
        # Validate and parse the incoming request data
        create_crimson_defense_acc_request: CreateCrimsonDefenseRequest = CreateCrimsonDefenseRequest.model_validate_json(request.data)
        create_crimson_defense_acc_dict: Dict = create_crimson_defense_acc_request.model_dump()
        create_crimson_defense_acc_dict['created_at'] = datetime.now()

        # Extract necessary information from the request data
        crimson_defense_email = create_crimson_defense_acc_dict["email"]  # Assuming the email is passed in the request
        email_exists =  client[db_name][db_accounts_collection].find_one({"email":crimson_defense_email})
        if email_exists:
            logging.error("The user's email is already in the database.")
            return jsonify({"error": "Eror Creating Accout. Check Server Logs."}), status.UNAUTHORIZED
        # Generate password and salt, then hash the password
        password = generate_password()
        hashed_password = bcrypt_hash_password(password)

        # Log the unsalted password for testing purposes
        logging.info(f"Generated unsalted password for testing: {password}")

        # Prepare account dictionary
        crimson_defense_account_dict = {
            "competition_id": None,  # Assuming the competition ID is not provided in this route
            "email": crimson_defense_email,
            "password": hashed_password,  # Store the salted and hashed password
            "role": "crimson_defense",
        }

        # Insert the account into the Accounts collection and get the new account's ID
        response = client[db_name][db_accounts_collection].insert_one(crimson_defense_account_dict)

        if response.inserted_id is None:
            return jsonify({"error": "Registration failed"}), status.INTERNAL_SERVER_ERROR

        email_request = EmailRequest(
            email_account=crimson_defense_email,
            subject="UA CTF Account Details",
            message=f"""
Dear Crimson Defense Member,

Your account has been successfully created. Here are your login credentials:
Email: {crimson_defense_email}
Password: {password}

Best regards,
The Team
            """.strip()
        )

        email_attempt_successful = send_email_to_user(email_request)
        if not email_attempt_successful:
            logging.error(f"Failed to send welcome email to {crimson_defense_email}")
            return jsonify({"error": "Could not send email to the Crimson Defense member"}), status.INTERNAL_SERVER_ERROR
        # Return success response
        return jsonify({
            "content": "Created account successfully!",
            "role": "crimson_defense",
            "email": crimson_defense_email,
            }), status.CREATED

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"content": "Request does not have all parameters required or adhere to the schema."}), status.BAD_REQUEST

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"content": "Error creating account"}), status.INTERNAL_SERVER_ERROR

# SUPER ADMIN ACCOUNTS ----------------------------------------------------
@accounts_blueprint.route('/accounts/admin/create', methods=["POST"])
def create_admin_account() -> Tuple[Response, int]:
    try:
        # Validate and parse the incoming request data
        create_admin_request: CreateAdminRequest = CreateAdminRequest.model_validate_json(request.data)
        create_admin_dict: Dict = create_admin_request.model_dump()
        create_admin_dict['created_at'] = datetime.now()

        # Extract necessary information from the request data
        admin_email = create_admin_dict["email"]  # Assuming the email is passed in the request
        email_exists =  client[db_name][db_accounts_collection].find_one({"email":admin_email})
        if email_exists["_id"]:
            logging.error("The user's email is already in the database.")
            return jsonify({"error": "Eror Creating Accout. Check Server Logs."}), status.UNAUTHORIZED

        # Generate password and salt, then hash the password
        password = generate_password()
        hashed_password = bcrypt_hash_password(password)

        # Log the unsalted password for testing purposes
        logging.info(f"Generated unsalted password for testing: {password}")

        # Prepare account dictionary
        admin_dict = {
            "competition_id": None,  # Assuming the competition ID is not provided in this route
            "email": admin_email,
            "password": hashed_password,  # Store the salted and hashed password
            "role": "admin",
        }

        # Insert the account into the Accounts collection and get the new account's ID
        response = client[db_name][db_accounts_collection].insert_one(admin_dict)

        if response.inserted_id is None:
            return jsonify({"error": "Registration failed"}), status.INTERNAL_SERVER_ERROR

        email_request = EmailRequest(
            email_account=admin_email,
            subject="UA CTF Account Details",
            message=f"""
Dear Administrator,

Your account has been successfully created. Here are your login credentials:
Email: {admin_email}
Password: {password}


Best regards,
The Team
            """.strip()
        )

        email_attempt_successful = send_email_to_user(email_request)
        if not email_attempt_successful:
            logging.error(f"Failed to send welcome email to {admin_email}")
            return jsonify({"error": "Could not send email to the administrator"}), status.INTERNAL_SERVER_ERROR

        # Return success response
        return jsonify({
            "content": "Created account successfully!",
            "role": "admin",
            "email": admin_email,
            }), status.CREATED

    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"content": "Request does not have all parameters required or adhere to the schema."}), status.BAD_REQUEST

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"content": "Error creating account"}), status.INTERNAL_SERVER_ERROR
