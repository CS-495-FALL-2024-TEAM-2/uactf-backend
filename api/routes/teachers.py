from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import GetAllTeachersResponse, teacher_info

teachers_blueprint = Blueprint("teachers", __name__)

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_teachers_collection = current_app.config['DB_TEACHER_INFO_COLLECTION']

@teachers_blueprint.route('/teachers/get/all')
def get_teams() -> Tuple[Response, int]:
    try:        
        db = client[db_name]
        collection = db[db_teachers_collection]

        teachers = []
        for document in collection.find():
                teacher = {
                    "account_id": str(document["account_id"]),
                    "first_name": document["first_name"],
                    "last_name": document["last_name"],
                    "school_name": document["school_name"],
                    "contact_number": document["contact_number"],
                    "shirt_size": document["shirt_size"],
                    "school_address": document["school_address"],
                    "school_website": document["school_website"],
                }
                
                validated_teacher: teacher_info = teacher_info.model_validate(teacher)
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
