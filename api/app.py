from flask import Flask, json, jsonify, Response, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import WriteError, OperationFailure
import os
import logging
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
from datetime import datetime
from pydantic import ValidationError
import http_status_codes as status
from bson.objectid import ObjectId
from models import CreateChallengeRequest, ListChallengeResponse, GetChallengeResponse
from flask_cors import CORS

load_dotenv()



db_user_name: Optional[str] = os.environ.get("DB_USERNAME",None)
db_password: Optional[str] = os.environ.get("DB_PASSWORD", None)
db_name = "crimsondefense_ctf"
db_challenges_collection = "challenges"
uri: Optional[str] = None

if db_user_name is None:
    logging.error("The environment variable DB_USERNAME was not set.")
elif db_password is None:
    logging.error("The environment variable DB_PASSWORD was not set.")
else:
    db_login_info: str = db_user_name + ":" + db_password
    uri = "mongodb+srv://" + db_login_info + "@cluster0.jpqva.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

if uri is not None:
    client: MongoClient = MongoClient(uri, server_api=ServerApi('1'))
else:
    logging.error("Url is None and Mongo Client could not be initialized.")


app = Flask(__name__)
CORS(app)

@app.route("/")
def get_main_route() -> Tuple[Response, int]:
    return jsonify({"content" : "Welcome to the UA CTF Backend!"}), status.OK

@app.route("/testdb")
def ping_to_test() -> Tuple[Response, int]:
    if uri is None:
        return jsonify({"error" : "Failed to Ping Database Successfully."}), status.INTERNAL_SERVER_ERROR
    try:
        client: MongoClient = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        return jsonify({"content": "Ping was successful. The database connection is operational."}), status.OK

    except Exception as e:
        logging.error("Encountered exception: %s", e)
    
    return jsonify({"error": "Error pinging database."}), status.INTERNAL_SERVER_ERROR

@app.route('/challenges/create', methods=["POST"])
def create_challenge() -> Tuple[Response, int]:
    try:
        create_challenge_request: CreateChallengeRequest = CreateChallengeRequest.model_validate_json(request.data)
        create_challenge_dict: Dict = create_challenge_request.model_dump()
        create_challenge_dict['created_at'] = datetime.now()
        db = client[db_name]
        collection = db[db_challenges_collection]
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

@app.route('/challenges/get')
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

    
@app.route('/challenges/details')
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
            "hints": document.get("hints", None)
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


