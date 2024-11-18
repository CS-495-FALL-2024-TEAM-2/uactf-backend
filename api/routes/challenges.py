from os import stat
from flask import Blueprint, json, jsonify, Response, request, current_app, url_for
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
import logging
from models import CreateChallengeRequest, ListChallengeResponse, GetChallengeResponse
import gridfs
from io import BytesIO

challenges_blueprint = Blueprint("challenges", __name__)

client = current_app.client
uri = current_app.uri
db_name = current_app.config['DB_NAME']
db_challenges_collection = current_app.config['DB_CHALLENGES_COLLECTION']


@challenges_blueprint.route('/challenges/create', methods=["POST"])
def create_challenge() -> Tuple[Response, int]:
    try:
        create_challenge_request: CreateChallengeRequest = CreateChallengeRequest.model_validate_json(request.form.get('challenge'))
        create_challenge_dict: Dict = create_challenge_request.model_dump()
        create_challenge_dict['created_at'] = datetime.now()
        db = client[db_name]
        collection = db[db_challenges_collection]
        challenge_file_attachment_id = None
        fs = gridfs.GridFS(db)
       
        # save file if present
        if 'challenge_file_attachment' in request.files:
            file = request.files['challenge_file_attachment']
            challenge_file_attachment_id = fs.put(file, filename=file.filename)

        create_challenge_dict['challenge_file_attachment_id'] = challenge_file_attachment_id
        response = collection.insert_one(create_challenge_dict)

        if response.inserted_id is not None:
            return jsonify({
                "content" : "Created Challenge Successfully!",
                "challenge_id": str(response.inserted_id)
                }),status.CREATED
        else:
            return jsonify({"error": "Error adding challenge to collection"}), status.INTERNAL_SERVER_ERROR

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
        return jsonify({"error": "Error creating challenge."}), status.INTERNAL_SERVER_ERROR


@challenges_blueprint.route('/challenges/get')
def get_challenges() -> Tuple[Response, int]:
    try:

        db = client[db_name]
        collection = db[db_challenges_collection]

        year: Optional[int] = None

        if 'year' in request.args:
            year = int(request.args['year'])

        challenges = []

        if year is None:
            logging.info("Client did not provide year parameter for getting the challenge.")
            for document in collection.find():
                challenge = {
                        "challenge_name": document["challenge_name"],
                        "challenge_category": document["challenge_category"],
                        "points": document["points"],
                        "challenge_description": document["challenge_description"],
                        "challenge_id": str(document["_id"]),
                        "division": document["division"]
                    }
                validated_challenge: ListChallengeResponse = ListChallengeResponse.model_validate(challenge)
                challenge_dict = validated_challenge.model_dump()
                challenges.append(challenge_dict)

            return jsonify({"content": "Successfully fetched challenges.", "challenges": challenges}), status.OK

        else:

            year_start = datetime(year, 1, 1)
            year_end = datetime(year + 1, 1, 1)

            query = {
                "created_at": {
                    "$gte": year_start,
                    "$lt": year_end
                }
            }

            for document in collection.find(query):
                challenge = {
                        "challenge_name": document["challenge_name"],
                        "challenge_category": document["challenge_category"],
                        "points": document["points"],
                        "challenge_description": document["challenge_description"],
                        "challenge_id": str(document["_id"]),
                        "division": document["division"],
                    }
                validated_challenge: ListChallengeResponse = ListChallengeResponse.model_validate(challenge)
                challenge_dict = validated_challenge.model_dump()
                challenges.append(challenge_dict)

            return jsonify({"content": "Successfully fetched challenges.", "challenges": challenges}), status.OK


    except ValueError as e:
          logging.error("ValueError: %s", e)
          return jsonify({'error': 'Year Parameter provided in request was not an int.'}), status.INTERNAL_SERVER_ERROR

    except WriteError as e:
          logging.error("WriteError: %s", e)
          return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error getting challenges."}), status.INTERNAL_SERVER_ERROR


@challenges_blueprint.route('/challenges/details')
def get_challenge_details():
    try:

        db = client[db_name]
        collection = db[db_challenges_collection]
        challenge_id: Optional[str] = None

        if 'challenge_id' in request.args:
            challenge_id = request.args['challenge_id']

        if challenge_id is None:
            return jsonify({"error": "challenge_id parameter is required."}), status.BAD_REQUEST

        document = collection.find_one({"_id": ObjectId(challenge_id)})

        if document is None:
            return jsonify({"error":"Could not find any challenge with that challenge_id"}), status.BAD_REQUEST

        challenge_file_attachment = None
        if "challenge_file_attachment_id" in document and document["challenge_file_attachment_id"] != None:
            challenge_file_attachment = url_for('files.download_file', file_id=document["challenge_file_attachment_id"], _external=True)

        challenge = {
            "challenge_name": document["challenge_name"],
            "points": document["points"],
            "creator_name": document["creator_name"],
            "division": document["division"],
            "challenge_description": document["challenge_description"],
            "flag": document["flag"],
            "is_flag_case_sensitive": document["is_flag_case_sensitive"],
            "challenge_category": document["challenge_category"],
            "solution_explanation": document["solution_explanation"],
            "hints": document.get("hints", None),
            "challenge_file_attachment": challenge_file_attachment,
        }

        validated_challenge: GetChallengeResponse = GetChallengeResponse.model_validate(challenge)
        challenge_dict = validated_challenge.model_dump()

        return jsonify({"content": "Successfully fetched challenge details.", "challenge": challenge_dict}), status.OK

    except ValueError as e:
        logging.error("ValueError: %s", e)
        return jsonify({'error': 'challenge_id provided was not a string'}), status.INTERNAL_SERVER_ERROR

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"content": "Error getting challenge details."}), status.INTERNAL_SERVER_ERROR

@challenges_blueprint.route('/challenges/<string:challenge_id>', methods=["PUT","DELETE"])
def update_or_delete_challenge(challenge_id: str) -> Tuple[Response, int]:
    try:
        db = client[db_name]
        collection = db[db_challenges_collection]
        fs = gridfs.GridFS(db)
        challenge = collection.find_one({"_id": ObjectId(challenge_id)})
        if challenge is None:
            return jsonify({"error":"Could not find any challenge with that challenge_id"}), status.BAD_REQUEST

        if request.method == "DELETE":
            # if the challenge has a file, delete the file
            if "challenge_file_attachment_id" in challenge and challenge["challenge_file_attachment_id"] != None:
                fs.delete(challenge["challenge_file_attachment_id"])

            delete_attempt = collection.delete_one({"_id": ObjectId(challenge_id)})

            if delete_attempt.deleted_count == 1:
                return jsonify({"content": "Deleted challenge successfully!"}), status.OK

            else:
                return jsonify({"error": "Failed to delete challenge"}), status.INTERNAL_SERVER_ERROR

        if request.method == "PUT":
            update_challenge_request: CreateChallengeRequest = CreateChallengeRequest.model_validate_json(request.form.get('challenge'))
            update_data: Dict = update_challenge_request.model_dump()
            
            # delete challenge file
            if request.form.get("delete_old_challenge_file") == "true":
                if "challenge_file_attachment_id" in challenge and challenge["challenge_file_attachment_id"] != None:
                    fs.delete(challenge["challenge_file_attachment_id"])
                    update_data['challenge_file_attachment_id'] = None

            # update challenge file if new file is present
            if 'challenge_file_attachment' in request.files:
                file = request.files['challenge_file_attachment']
                new_challenge_file_attachment_id = fs.put(file, filename=file.filename)
                update_data['challenge_file_attachment_id'] = new_challenge_file_attachment_id

            update_attempt = collection.update_one(
                    {"_id": ObjectId(challenge_id)},
                    {"$set": update_data}
                    )

            if update_attempt.modified_count == 1:
                return jsonify({"content": "Successfully updated challenge!"}), status.OK
            else:
                return jsonify({"content": "Warning. No changes were made"}), status.OK
        else:
            return jsonify({"error": "Endpoint does not support this method"}), status.NOT_IMPLEMENTED

    except ValidationError as e:
        return jsonify({"error": str(e)}), status.BAD_REQUEST

    except WriteError as e:
        logging.error("WriteError: %s", e)
        return jsonify({'error': 'An error occurred while reading from the database.'}), status.INTERNAL_SERVER_ERROR

    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({"error": "Error updating or deleting challenge"}), status.INTERNAL_SERVER_ERROR
