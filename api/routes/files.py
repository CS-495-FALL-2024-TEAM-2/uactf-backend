
from io import BytesIO
from bson.objectid import ObjectId
from flask import Blueprint, current_app, jsonify, send_file
import gridfs
import gridfs.errors

files_blueprint = Blueprint("files", __name__)
db_name = current_app.config['DB_NAME']
client = current_app.client
db = client[db_name]
fs = gridfs.GridFS(db)

@files_blueprint.route('/files/<file_id>', methods=['GET'])
def download_file(file_id):
    try:
        # Retrieve the file from GridFS
        print(file_id)
        file = fs.get(ObjectId(file_id))
        return send_file(
            BytesIO(file.read()), 
            download_name=file.filename, 
            mimetype=file.content_type
        )
    except gridfs.errors.NoFile:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500