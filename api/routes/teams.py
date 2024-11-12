from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import GetTeamByTeacherResponse, CreateTeamRequest, student_info

teams_blueprint = Blueprint("teams", __name__)


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
        create_team_dict['created_at'] = datetime.now()
        db = client[db_name]
        collection = db[db_teams_collection]
        response = collection.insert_one(create_team_dict)

        if response.inserted_id is not None:
            return jsonify({
                "content" : "Created team Successfully!",
                "competition_id": str(response.inserted_id)
                }),status.CREATED
        else:
            return jsonify({"error": "Error adding team to collection"}), status.INTERNAL_SERVER_ERROR

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
        if teacher_id is None:
            return jsonify({"error": "teacher_id parameter is required."}), status.BAD_REQUEST

        team_document = team_collection.find_one({"_id": ObjectId(teacher_id)})

        if team_document is None:
            return jsonify({"error":"Could not find any team related to that teacher_id"}), status.BAD_REQUEST
        
        team = {
            "competition_id": team_document["competition_id"],
            "name": team_document["name"],
            "division": team_document["division"],
            "is_virtual": team_document["is_virtual"],
        }

        students = []
        query = {"teacher_id": teacher_id}
        for document in student_collection.find(query):
                student = {
                    "student_account_id": document[""],
                    "first_name": document["first_name"],
                    "last_name": document["last_name"],
                    "shirt_size": document["shirt_size"],
                    "liability_form": document["liability_form"],
                    "upload_date": document["upload_date"],
                    "is_verified": document["is_verified"],
                }
                validated_student: student_info = student_info.model_validate(student)
                student_dict = validated_student.model_dump()
                students.append(student_dict)

        team["students"] = students
        validated_team: GetTeamByTeacherResponse = GetTeamByTeacherResponse.model_validate(team)
        team_dict = validated_team.model_dump()

        return jsonify({"content": "Successfully fetched teams.", "team": team_dict}), status.OK

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting team information."}), status.INTERNAL_SERVER_ERROR
