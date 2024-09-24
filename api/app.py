from flask import Flask, jsonify, Response, request
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
from models import CreateChallengeRequest

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

@app.route("/")
def get_main_route() -> Tuple[Response, int]:
    return jsonify({"content" : "Welcome to the UA CTF Backend!"}), status.OK

@app.route("/testdb")
def ping_to_test() -> Tuple[Response, int]:
    if uri is None:
        return jsonify({"content" : "Failed to Ping Database Successfully."}), status.INTERNAL_SERVER_ERROR
    try:
        client: MongoClient = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        return jsonify({"content": "Ping was successful. The database connection is operational."}), status.OK

    except Exception as e:
        logging.error("Encountered exception: %s", e)
    
    return jsonify({"content": "Error pinging database."}), status.INTERNAL_SERVER_ERROR

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
            return jsonify({"Error adding challenge to collection"}), status.INTERNAL_SERVER_ERROR

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
    
    return jsonify({"content": "Error creating challenge."}), status.INTERNAL_SERVER_ERROR


