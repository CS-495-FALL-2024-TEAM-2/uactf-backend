from flask import Blueprint, jsonify, Response, request, current_app, url_for
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import GetAllTeachersResponse, StudentInfoResponse, TeacherInfo

admin_blueprint = Blueprint("admin", __name__)

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_students_collection: str = current_app.config['DB_STUDENT_INFO_COLLECTION']


# TODO: TEST
@admin_blueprint.route('/admin/get-students-to-be-verified')
def get_students_to_be_verified() -> Tuple[Response, int]:
    try:
        db = client[db_name]
        student_collection = db[db_students_collection]
        students = []

        for document in student_collection.find({"is_verified": False, "liability_form_id": {"$exists": True, "$ne": None }}):
            print(document)
            student = {
                "id": str(document["_id"]),
                "student_account_id": str(document["student_account_id"]),
                "first_name": document["first_name"],
                "last_name": document["last_name"],
                "email": document["email"],
                "shirt_size": document["shirt_size"],
                "signed_liability_release_form": url_for('files.download_file', file_id=document["liability_form_id"], _external=True),
                "is_verified": document["is_verified"]
            }

            validated_student: StudentInfoResponse = StudentInfoResponse.model_validate(student)
            student_dict = validated_student.model_dump()
            students.append(student_dict)

        return jsonify({"content": "Successfully fetched students.", "students": students}), status.OK

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting student information."}), status.INTERNAL_SERVER_ERROR


# TODO: TEST
@admin_blueprint.route('/admin/verify-student/<string:student_id>', methods=["POST"])
def verify_student(student_id) -> Tuple[Response, int]:
    try:
        db = client[db_name]
        student_collection = db[db_students_collection]
        
        # check that student exists
        student = student_collection.find_one({"_id": ObjectId(student_id)})
        if student is None:
            return jsonify({"error":"Could not find student with that id"}), status.BAD_REQUEST

        # check that signed liability form exists
        if "liability_form_id" in student and student["liability_form_id"] != None:
            # set is_verified to true
            update_attempt = student_collection.update_one(
                {"_id": ObjectId(student["_id"])},
                {"$set": {"is_verified": True}}
            )

            if update_attempt.modified_count == 1:
                return jsonify({"content": "Successfully uploaded signed form!"}), status.OK
            else:
                return jsonify({"warning": "No changes were made!"}), status.OK
        else:
            return jsonify({"error": "Student does not have signed liability form uploaded"}), status.BAD_REQUEST

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting student information."}), status.INTERNAL_SERVER_ERROR
    

    

    