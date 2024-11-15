from flask import Blueprint, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import date, datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import CreateCompetitionRequest, GetCompetitionResponse

competitions_blueprint = Blueprint("competitions", __name__)

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_competitions_collection = current_app.config['DB_COMPETITION_COLLECTION']


@competitions_blueprint.route('/competitions/create', methods=["POST"])
def create_competition() -> Tuple[Response, int]:
    try:
        create_competition_request: CreateCompetitionRequest = CreateCompetitionRequest.model_validate_json(request.data)

        create_competition_dict: Dict = create_competition_request.model_dump()
        create_competition_dict['created_at'] = datetime.now()
        db = client[db_name]
        collection = db[db_competitions_collection]
        response = collection.insert_one(create_competition_dict)

        if response.inserted_id is not None:
            return jsonify({
                "content" : "Created competition Successfully!",
                "competition_id": str(response.inserted_id)
                }),status.CREATED
        else:
            return jsonify({"error": "Error adding competition to collection"}), status.INTERNAL_SERVER_ERROR

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

    return jsonify({"error": "Error creating competition."}), status.INTERNAL_SERVER_ERROR

@competitions_blueprint.route('/competitions/get')
def get_competitions() -> Tuple[Response, int]:
    try:

        db = client[db_name]
        collection = db[db_competitions_collection]

        competitions = []

        for document in collection.find():
                competition = {
                    "competition_id": str(document["_id"]),
                    "competition_name": document["competition_name"],
                    "created_at": document["created_at"],
                    "registration_deadline": document["registration_deadline"],
                    "is_active": document["is_active"]
                }
                validated_competition: GetCompetitionResponse = GetCompetitionResponse.model_validate(competition)
                competition_dict = validated_competition.model_dump()
                competitions.append(competition_dict)
        return jsonify({"content": "Successfully fetched competitions.", "competitions": competitions}), status.OK

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error getting competitions."}), status.INTERNAL_SERVER_ERROR

@competitions_blueprint.route('/competitions/get/current')
def get_current_competitions() -> Tuple[Response, int]:
    try:

        db = client[db_name]
        collection = db[db_competitions_collection]

        today = datetime.now()
        query = {"registration_deadline": {"$gt": today}, "is_active": True}

        competitions = []

        for document in collection.find(query):
                competition = {
                    "competition_id": str(document["_id"]),
                    "competition_name": document["competition_name"],
                    "created_at": document["created_at"],
                    "registration_deadline": document["registration_deadline"],
                    "is_active": document["is_active"]
                }
                validated_competition: GetCompetitionResponse = GetCompetitionResponse.model_validate(competition)
                competition_dict = validated_competition.model_dump()
                competitions.append(competition_dict)

        return jsonify({"content": "Successfully fetched competitions.", "competitions": competitions}), status.OK

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting competitions."}), status.INTERNAL_SERVER_ERROR

@competitions_blueprint.route('/competitions/details')
def get_competition_details():
    try:

        db = client[db_name]
        collection = db[db_competitions_collection]
        competition_id: Optional[str] = None

        if 'competition_id' in request.args:
            competition_id = request.args['competition_id']

        if competition_id is None:
            return jsonify({"error": "competition_id parameter is required."}), status.BAD_REQUEST

        document = collection.find_one({"_id": ObjectId(competition_id)})

        if document is None:
            return jsonify({"error":"Could not find any competition with that competition_id"}), status.BAD_REQUEST

        competition = {
            "competition_id": str(document["_id"]),
            "competition_name": document["competition_name"],
            "created_at": document["created_at"],
            "registration_deadline": document["registration_deadline"],
            "is_active": document["is_active"]
        }

        validated_competition: GetCompetitionResponse = GetCompetitionResponse.model_validate(competition)
        competition_dict = validated_competition.model_dump()

        return jsonify({"content": "Successfully fetched competition details.", "competition": competition_dict}), status.OK

    except ValueError as e:
        logging.error("ValueError: %s", e)
        return jsonify({'error': 'competition_id provided was not a string'}), status.INTERNAL_SERVER_ERROR

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)

    return jsonify({"content": "Error getting competition details."}), status.INTERNAL_SERVER_ERROR


@competitions_blueprint.route('/competitions/<string:competition_id>', methods=["POST", "DELETE"])
def update_or_delete_competition(competition_id) -> Tuple[Response, int]:
    try:
        if not ObjectId.is_valid(competition_id):
            return jsonify({"error": "Invalid competition ID"}), 400
        
        db = client[db_name]
        collection = db[db_competitions_collection]

        if request.method == "DELETE":
            delete_attempt = collection.delete_one({"_id": ObjectId(competition_id)})

            if delete_attempt.deleted_count == 1:
                return jsonify({"content": "Deleted competition successfully!"}), status.OK

            else:
                return jsonify({"error": "Failed to delete competition"}), status.INTERNAL_SERVER_ERROR

        elif request.method == "PUT":
            update_competition_dict: Dict = request.get_json()
            if "is_active" in update_competition_dict:
                value = update_competition_dict['is_active']
                if isinstance(value, str):
                    if value.lower() in ['true', '1']:
                        update_competition_dict['is_active'] = True
                    elif value.lower() in ['false', '0']:
                        update_competition_dict['is_active'] = False

            response = collection.update_one({"_id": ObjectId(competition_id)}, {"$set": update_competition_dict})
            if response.matched_count > 0 and response.modified_count > 0:
                return jsonify({
                    "content" : "Update competition Successfully!",
                    }),status.CREATED
            else:
                return jsonify({"error": "Error updating competition in the collection"}), status.INTERNAL_SERVER_ERROR
        else:
            return jsonify({"error": "Endpoint does not support this method"}), status.NOT_IMPLEMENTED

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

    return jsonify({"error": "Error updating competition."}), status.INTERNAL_SERVER_ERROR
