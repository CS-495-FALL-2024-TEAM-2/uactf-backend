from flask import Flask
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import logging

db_user_name = os.environ.get("DB_USERNAME",None)
db_password = os.environ.get("DB_PASSWORD", None)
uri = None
if db_user_name is None:
    logging.error("The environment variable DB_USERNAME was not set.")
elif db_password is None:
    logging.error("The environment variable DB_PASSWORD was not set.")
else:
    db_login_info = db_user_name + ":" + db_password
    uri = "mongodb+srv://" + db_login_info + "@cluster0.jpqva.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


app = Flask(__name__)

@app.route("/")
def get_main_route():
    return {"content" : "Welcome to the UA CTF Backend!"}, 200

@app.route("/testdb")
def ping_to_test():
    if uri is None:
        return {"content" : "Failed to Ping Database Successfully."}, 503
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        return {"content": "Ping was successful. The database connection is operational."}, 200
    except Exception as e:
        logging.error("Encountered exception: %s", e)
    
    return {"content": "Error pinging database."}, 500

