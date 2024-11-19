import os
from flask import Blueprint, jsonify, Response, request, current_app, url_for
from typing import Dict, Optional, Tuple

import jwt
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
import gridfs
from models import GetAllTeachersResponse, TeacherInfo

teachers_blueprint = Blueprint("teachers", __name__)
secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_students_collection: str = current_app.config['DB_STUDENT_INFO_COLLECTION']
db_teams_collection: str = current_app.config['DB_TEAMS_COLLECTION']
db_teachers_collection: str = current_app.config['DB_TEACHER_INFO_COLLECTION']


@teachers_blueprint.route('/teachers/get/all')
def get_teams() -> Tuple[Response, int]:
    try:
        db = client[db_name]
        collection = db[db_teachers_collection]

        teachers = []
        for document in collection.find():
                teacher = {
                    "id": str(document["_id"]),
                    "account_id": str(document["account_id"]),
                    "first_name": document["first_name"],
                    "last_name": document["last_name"],
                    "school_name": document["school_name"],
                    "contact_number": document["contact_number"],
                    "shirt_size": document["shirt_size"],
                    "school_address": document["school_address"],
                    "school_website": document["school_website"],
                }

                validated_teacher: TeacherInfo = TeacherInfo.model_validate(teacher)
                teacher_dict = validated_teacher.model_dump()
                teachers.append(teacher_dict)

        return jsonify({"content": "Successfully fetched teachers.", "teachers": teachers}), status.OK

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting teacher information."}), status.INTERNAL_SERVER_ERROR


@teachers_blueprint.route('/teachers/upload-signed-liability-release-form', methods=["POST"])
def upload_signed_liability_release_form() -> Tuple[Response, int]:
    try:
        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]
        fs = gridfs.GridFS(db)


        # check that liability form exists
        if 'signed_liability_release_form' not in request.files:
            return jsonify({"error": "No signed liability release form attached!"}), status.BAD_REQUEST
        # check that student id is in request
        student_id = request.form.get('student_id')
        if student_id == None:
            return jsonify({"error": "No student id present"}), status.BAD_REQUEST

        # get teacher id
        token = request.cookies.get("access_token")
        decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm]) if token else None

        if not decoded_token:
            return jsonify({'error': "Unauthorized "}), status.UNAUTHORIZED
        teacher_id = decoded_token["userId"]
        

        student = student_collection.find_one({"_id": ObjectId(student_id)})
        if student is None:
            return jsonify({"error":"Could not find student with that id"}), status.BAD_REQUEST
        
        team = team_collection.find_one({"_id": ObjectId(student["team_id"])})

        # check if teacher is the teacher for the team the student belongs to
        if team["teacher_id"] != teacher_id:
            return jsonify({"error":"Invalid request"}), status.BAD_REQUEST

        if "liability_form_id" in student and student["liability_form_id"] != None:
            # delete old form
            fs.delete(student["liability_form_id"])

        # upload new signed form
        file = request.files['signed_liability_release_form']
        new_liability_form_id = fs.put(file, filename=file.filename)

        update_data = {
            "liability_form_id": new_liability_form_id
        }

        if student["is_verified"] == True:
            # if is_verified, change is_verified to false
            update_data["is_verified"] = False
        
        update_attempt = student_collection.update_one(
            {"_id": ObjectId(student["_id"])},
            {"$set": update_data}
            )

        if update_attempt.modified_count == 1:
            return jsonify({"content": "Successfully uploaded signed form!"}), status.OK
        
    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error uploading signed liability release form"}), status.INTERNAL_SERVER_ERROR