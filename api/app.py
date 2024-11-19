from flask import Flask, jsonify, Response, request
import os
from config import config
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv
import http_status_codes as status
from flask_cors import CORS
from middleware import Middleware

load_dotenv()


def create_app(config_name="dev"):
    app = Flask(__name__)
    app.app_context().push()
    app.config.from_object(config[config_name])
    app.wsgi_app = Middleware(app.wsgi_app)

    # Enable CORS
    CORS(app, supports_credentials=True,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', '*'],
        expose_headers=["Set-Cookie", "Access-Control-Allow-Credentials"],
        resources={r"/*": {"origins": app.config['CLIENT_ORIGIN']}})

    app.config['CORS_HEADERS'] = 'Content-Type'

    # Check if testing
    if app.config['TESTING']:
        return app

    # Check for configs
    uri: Optional[str] = None
    if not app.config['DB_USERNAME']:
        logging.error("The environment variable DB_USERNAME was not set.")
    elif not app.config['DB_PASSWORD']:
        logging.error("The environment variable DB_PASSWORD was not set.")
    else:
        db_login_info: str = app.config['DB_USERNAME'] + ":" + app.config['DB_PASSWORD']
        uri = "mongodb+srv://" + db_login_info + "@cluster0.jpqva.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

    # Init MongoDB client
    try:
        if uri is not None:
            client: MongoClient = MongoClient(uri, server_api=ServerApi('1'))

            app.uri = uri
            app.client = client
    except Exception as e:
        logging.error(f"Failed to initialize MongoDB client: {e}")


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



    # Register routes here
    from routes.challenges import challenges_blueprint
    from routes.refresh import refresh_blueprint
    from routes.authentication import auth_blueprint
    from routes.accounts import accounts_blueprint
    from routes.competitions import competitions_blueprint
    from routes.teachers import teachers_blueprint
    from routes.teams import teams_blueprint
    from routes.files import files_blueprint
    from routes.reports import reports_blueprint
    from routes.admin import admin_blueprint

    app.register_blueprint(challenges_blueprint)
    app.register_blueprint(refresh_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(accounts_blueprint)
    app.register_blueprint(competitions_blueprint)
    app.register_blueprint(teachers_blueprint)
    app.register_blueprint(teams_blueprint)
    app.register_blueprint(files_blueprint)
    app.register_blueprint(reports_blueprint)
    app.register_blueprint(admin_blueprint)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=5000, debug=True)
