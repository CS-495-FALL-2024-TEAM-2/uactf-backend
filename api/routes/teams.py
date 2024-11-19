import token
from urllib import response
from flask import Blueprint, jsonify, Response, request, current_app, url_for
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import CreateTeamRequest, GetTeamResponse
from usernames import generate_username
from passwords import generate_password
import jwt
import os

teams_blueprint = Blueprint("teams", __name__)
secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")


client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_teams_collection = current_app.config['DB_TEAMS_COLLECTION']
db_students_collection = current_app.config['DB_STUDENT_INFO_COLLECTION']
db_student_accounts_collection: str = current_app.config['DB_STUDENT_ACCOUNTS_COLLECTION']
db_team_accounts_collection: str = current_app.config["DB_TEAM_ACCOUNTS_COLLECTION"]


@teams_blueprint.route('/teams/create', methods=["POST"])
def create_competition() -> Tuple[Response, int]:
    try:
        create_team_request: CreateTeamRequest = CreateTeamRequest.model_validate_json(request.data)

        create_team_dict: Dict = create_team_request.model_dump()

        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]
        student_accounts_collection = db[db_student_accounts_collection]
        team_accounts_collection = db[db_team_accounts_collection]

        team_members = create_team_dict.pop("team_members")

        # If teacher_id is not provided, get it from the token
        if not create_team_dict["teacher_id"]:
            # Get id from token in cookies
            token = request.cookies.get("access_token")
            decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm]) if token else None

            if not decoded_token:
                return jsonify({'error': "Unauthorized "}), status.UNAUTHORIZED

            create_team_dict["teacher_id"] = decoded_token["userId"]

        # TODO: Get current active competition id from the token and add it to the team
        create_team_dict["competition_id"] = "test_competition_id"

        # Create team in team database collection
        response = team_collection.insert_one(create_team_dict)

        if response.inserted_id is None:
            return jsonify({"error": "Error adding team to collection"}), status.INTERNAL_SERVER_ERROR

        # Create students in student database collection
        team_id = response.inserted_id
        team_name = create_team_dict["name"]
        team_username = generate_username(team_name)
        team_password = generate_password()

        team_account = {
                "team_id": ObjectId(team_id),
                "team_username": team_username,
                "team_password": team_password,
        }

        team_account_response = team_accounts_collection.insert_one(team_account)

        if team_account_response.inserted_id is None:
            return jsonify({"error": "Error creating team account."}), status.INTERNAL_SERVER_ERROR

        for student in team_members:

            student = {
                "team_id": team_id,
                "student_account_id": "test student account id",
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "shirt_size": student["shirt_size"],
                "email": student["email"] if "email" in student else None,
                "liability_form_id": None,
                "is_verified": False,
            }

            student_response = student_collection.insert_one(student)

            if student_response.inserted_id is None:
                return jsonify({"error": "Error adding student to collection"}), status.INTERNAL_SERVER_ERROR

            student_competition_username: str = generate_username(student["first_name"], student["last_name"])
            student_competition_password: str = generate_password()
            student_practice_username: str =  generate_username(student["first_name"], student["last_name"])
            student_practice_password: str = generate_password()
            
            student_account = {
                "competition_username": student_competition_username,
                "competition_password": student_competition_password,
                "practice_username": student_practice_username,
                "practice_password": student_practice_password,
                "student_info_id": ObjectId(student_response.inserted_id)
            }


            student_accounts_response = student_accounts_collection.insert_one(student_account)

            if student_accounts_response.inserted_id is None:
                return jsonify({"error": "Error creating student account."}), status.INTERNAL_SERVER_ERROR



        return jsonify({"content": "Created team Successfully!", "team_id": str(team_id)}), status.CREATED

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

    return jsonify({"error": "Error creating team."}), status.INTERNAL_SERVER_ERROR

@teams_blueprint.route('/teams/get')
def get_teams() -> Tuple[Response, int]:
    try:
        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]
        teacher_id: Optional[str] = None

        if 'teacher_id' in request.args:
            teacher_id = request.args['teacher_id']

        if not teacher_id:
            # Get id from token in cookies
            token = request.cookies.get("access_token")
            decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm]) if token else None

            if not decoded_token:
                return jsonify({'error': "Unauthorized "}), status.UNAUTHORIZED

            teacher_id = decoded_token["userId"]

        teams = []

        for document in team_collection.find({"teacher_id": teacher_id}):
            team = {
                "id": str(document["_id"]),
                "teacher_id": document["teacher_id"],
                "competition_id": document["competition_id"],
                "name": document["name"],
                "division": document["division"],
                "is_virtual": document["is_virtual"]
            }

            students = student_collection.find({"team_id": ObjectId(document["_id"])})

            students_list = []
            for student in students:
                signed_liability_release_form = None
                if "liability_form_id" in student and student["liability_form_id"] != None:
                    signed_liability_release_form = url_for('files.download_file', file_id=student["liability_form_id"], _external=True)
                student_info = {
                    "id": str(student["_id"]),
                    "student_account_id": student["student_account_id"],
                    "first_name": student["first_name"],
                    "last_name": student["last_name"],
                    "shirt_size": student["shirt_size"],
                    "signed_liability_release_form": signed_liability_release_form,
                    "is_verified": student["is_verified"],
                }

                students_list.append(student_info)

            team["students"] = students_list

            validated_team: GetTeamResponse = GetTeamResponse.model_validate(team)
            team_dict = validated_team.model_dump()
            teams.append(team_dict)

        return jsonify({"content": "Successfully fetched teams.", "teams": teams}), status.OK

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error getting team information."}), status.INTERNAL_SERVER_ERROR

@teams_blueprint.route('/teams/details')
def get_team_details() -> Tuple[Response, int]:
    try:
        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]
        team_id: Optional[str] = None

        if 'team_id' in request.args:
            team_id = request.args['team_id']

        if team_id is None:
            return jsonify({"error": "team_id parameter is required."}), status.BAD_REQUEST

        document = team_collection.find_one({"_id": ObjectId(team_id)})

        if document is None:
            return jsonify({"error":"Could not find any team with that team_id"}), status.BAD_REQUEST

        team = {
            "id": str(document["_id"]),
            "teacher_id": document["teacher_id"],
            "competition_id": document["competition_id"],
            "name": document["name"],
            "division": document["division"],
            "is_virtual": document["is_virtual"]
        }

        students = student_collection.find({"team_id": ObjectId(team_id)})

        students_list = [{
            "id": str(student["_id"]),
            "student_account_id": student["student_account_id"],
            "first_name": student["first_name"],
            "last_name": student["last_name"],
            "email": student["email"] if "email" in student else None,
            "shirt_size": student["shirt_size"],
            "is_verified": student["is_verified"],
        } for student in students]

        team["students"] = students_list

        validated_team: GetTeamResponse = GetTeamResponse.model_validate(team)
        team_dict = validated_team.model_dump()

        return jsonify({"content": "Successfully fetched team details.", "team": team_dict}), status.OK

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error getting team information."}), status.INTERNAL_SERVER_ERROR

@teams_blueprint.route('/teams/update/<string:team_id>', methods=["POST"])
def update_team(team_id) -> Tuple[Response, int]:
    try:
        if not ObjectId.is_valid(team_id):
            return jsonify({"error": "Invalid team_id"}), status.BAD_REQUEST

        update_team_dict: Dict = request.get_json()

        db = client[db_name]
        student_collection = db[db_students_collection]
        team_collection = db[db_teams_collection]

        # Update the students of the team if team_members is provided
        team_members = update_team_dict.pop("team_members")

        # Get the current team members from the database
        response = student_collection.find({"team_id": ObjectId(team_id)})
        current_team_members_ids = [str(student["_id"]) for student in response]

        for student in team_members:
            student_id = student["id"]

            if not student_id:
                # If student is not found, insert the student
                new_student = {
                    "team_id": ObjectId(team_id),
                    "student_account_id": "test student account id",
                    "first_name": student["first_name"],
                    "last_name": student["last_name"],
                    "email": student["email"] if "email" in student else None,
                    "liability_form_id": None,
                    "shirt_size": student["shirt_size"],
                    "is_verified": False,
                }

                student_response = student_collection.insert_one(new_student)

                if student_response.inserted_id is None:
                    return jsonify({"error": "Error adding student to collection"}), status.INTERNAL_SERVER_ERROR
            else:
                # If student is found, update the student
                response = student_collection.update_one({"_id": ObjectId(student_id)}, {"$set": student})

        # Remove students that are not in the updated team members
        for student_id in current_team_members_ids:
            if student_id not in [student["id"] for student in team_members]:
                print(student_id)
                response = student_collection.delete_one({"_id": ObjectId(student_id)})

                if response.deleted_count == 0:
                    return jsonify({"error": "Error deleting student from collection"}), status.INTERNAL_SERVER_ERROR

        # Update the team
        response = team_collection.update_one({"_id": ObjectId(team_id)}, {"$set": update_team_dict})

        if response.matched_count > 0:
            return jsonify({"content" : "Update team successfully!"}),status.CREATED
        else:
            return jsonify({"error": "Error updating team in the collection"}), status.INTERNAL_SERVER_ERROR

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
        return jsonify({"content": "Error updating team information."}), status.INTERNAL_SERVER_ERROR

@teams_blueprint.route('/teams/delete/<string:team_id>', methods=["DELETE"])
def delete_team(team_id) -> Tuple[Response, int]:
    try:
        if not ObjectId.is_valid(team_id):
            return jsonify({"error": "Invalid team_id"}), status.BAD_REQUEST

        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]

        # Delete the team
        response = team_collection.delete_one({"_id": ObjectId(team_id)})

        if response.deleted_count == 0:
            return jsonify({"error": "Error deleting team from collection"}), status.INTERNAL_SERVER_ERROR

        # Delete the students of the team
        response = student_collection.delete_many({"team_id": ObjectId(team_id)})

        if response.deleted_count == 0:
            return jsonify({"error": "Error deleting students from collection"}), status.INTERNAL_SERVER_ERROR

        return jsonify({"content": "Deleted team successfully!"}), status.OK

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while writing to the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error deleting team information."}), status.INTERNAL_SERVER_ERROR
