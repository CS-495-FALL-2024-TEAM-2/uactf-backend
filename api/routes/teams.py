import token
from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import GetTeamByTeacherResponse, CreateTeamRequest, StudentInfo
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


@teams_blueprint.route('/teams/create', methods=["POST"])
def create_competition() -> Tuple[Response, int]:
    try:
        create_team_request: CreateTeamRequest = CreateTeamRequest.model_validate_json(request.data)

        create_team_dict: Dict = create_team_request.model_dump()

        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]

        team_members = create_team_dict.pop("team_members")

        # Create team in team database collection
        response = team_collection.insert_one(create_team_dict)

        if response.inserted_id is None:
            return jsonify({"error": "Error adding team to collection"}), status.INTERNAL_SERVER_ERROR

        # Create students in student database collection
        team_id = response.inserted_id
        for student in team_members:
            # TODO: Generate a student account for the student first

            student = {
                "team_id": team_id,
                "student_account_id": "test student account id",
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "shirt_size": student["shirt_size"],
                "liability_form": "",
                "is_verified": student["is_verified"],
            }

            student_response = student_collection.insert_one(student)

            if student_response.inserted_id is None:
                return jsonify({"error": "Error adding student to collection"}), status.INTERNAL_SERVER_ERROR


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

            students_list = [{
                "id": str(student["_id"]),
                "student_account_id": student["student_account_id"],
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "shirt_size": student["shirt_size"],
                "liability_form": student["liability_form"],
                "is_verified": student["is_verified"],
            } for student in students]

            team["students"] = students_list

            validated_team: GetTeamByTeacherResponse = GetTeamByTeacherResponse.model_validate(team)
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