from flask import Blueprint, json, jsonify, Response, request, current_app
from typing import Dict, Optional, Tuple
import http_status_codes as status
from pymongo.errors import WriteError, OperationFailure
from datetime import datetime
from pydantic import ValidationError
from bson.objectid import ObjectId
from models import CreateTeamsReportRequest
import logging
from emails import EmailWithAttachmentRequest, send_email_with_attachment
import jwt
import io
import csv
import os
import base64


reports_blueprint = Blueprint("reports", __name__)
secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")

client = current_app.client
uri: str = current_app.uri
db_name: str = current_app.config['DB_NAME']

db_teams_collection: str = current_app.config['DB_TEAMS_COLLECTION']
db_accounts_collection: str = current_app.config['DB_ACCOUNTS_COLLECTION']
db_students_collection: str = current_app.config['DB_STUDENT_INFO_COLLECTION']
db_teachers_collection: str = current_app.config['DB_TEACHER_INFO_COLLECTION']

@reports_blueprint.route('/reports/teams/create', methods=["POST"])
def create_teams_report() -> Tuple[Response, int]:
    try:
        create_teams_report_request: CreateTeamsReportRequest = CreateTeamsReportRequest.model_validate_json(request.data)
        create_teams_report_dict: Dict = create_teams_report_request.model_dump()
        report_is_for_virtual_teams = create_teams_report_dict["is_virtual"]
        if report_is_for_virtual_teams:
            report_type = "Virtual"
        else:
            report_type = "In-Person"
        db = client[db_name]
        team_collection = db[db_teams_collection]
        student_collection = db[db_students_collection]
        accounts_collecion = db[db_accounts_collection]
        teachers_collection = db[db_teachers_collection]
        # The admin can pass an email address for the report to be sent to
        # If an email is not part of the request, it is sent to the admins email_account
        if request.args.get("email")!=None:
            email_account = request.args.get("email")
        else:
            token = request.cookies.get("access_token")
            if token:
                decoded_token = jwt.decode(token, secret_key, algorithms=[auth_algorithm])
            else:
                logging.error("Unable to get token from cookies")
                return jsonify({"error": "Internal Server Error. Check Server Logs"}), status.INTERNAL_SERVER_ERROR
            if not decoded_token:
                logging.error("Unable to decode token")
                return jsonify({"error": "Internal Server Error. Check Server Logs"}), status.INTERNAL_SERVER_ERROR

            admin_id = decoded_token["userId"]
            admin_info = accounts_collecion.find_one({"_id": ObjectId(admin_id)})
            if admin_info is None:
                return jsonify({"error": "Error getting admin info from server. Alternatively, try providing your email address directly."}), status.INTERNAL_SERVER_ERROR
            email_account = admin_info["email"]

        teams_of_type = list(team_collection.find({"is_virtual": report_is_for_virtual_teams}))
        if not teams_of_type:
            return jsonify({"error": f"Did not find any {report_type} teams in the database"}), status.INTERNAL_SERVER_ERROR
        
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "Instructor Information",
            "Division",
            "School Name",
            "Name",
            "Email",
            "Contact Number",
            "Shirt Size",
            "Student 1 Name",
            "Student 1 Shirt Size",
            "Student 1 Email",
            "Student 2 Name",
            "Student 2 Shirt Size",
            "Student 2 Email",
            "Student 3 Name",
            "Student 3 Shirt Size",
            "Student 3 Email",
            "Student 4 Name",
            "Student 4 Shirt Size",
            "Student 4 Email"
        ]
        writer.writerow(headers)

        # Process each team
        for team in teams_of_type:
            # Get teacher info
            teacher = teachers_collection.find_one({"_id": ObjectId(team["teacher_id"])})
            if not teacher:
                logging.error(f"Teacher not found for team {team['_id']}")
                continue
            team_id = team.get("_id")
            team_id = ObjectId(team_id)

            # Get students for this team
            students = students = list(student_collection.find({"team_id":ObjectId(team["_id"])}).limit(4))
            
            # Prepare row data
            row = [
                f"{teacher['first_name']} {teacher['last_name']}",
                ", ".join(str(d) for d in team["division"]),
                teacher["school_name"],
                team["name"],
                teacher["email"],
                teacher["contact_number"],
                teacher["shirt_size"]
            ]
            
            # Add student information (up to 4 students)
            for i in range(4):
                if i < len(students):
                    student = students[i]
                    row.extend([
                        f"{student['first_name']} {student['last_name']}",
                        student["shirt_size"],
                        student.get("email", "")
                    ])
                else:
                    row.extend(["", "", ""])

            writer.writerow(row)
        
        # Resetting buffer
        output.seek(0)
        content = output.getvalue()
        # Making sure its not just the header row or empty
        if content.count('\n') <= 1:
            return jsonify({'error': 'No valid team data could be processed for the report.'}), status.NOT_FOUND

        email_request = EmailWithAttachmentRequest(
            email_account=email_account,
            subject=f"{report_type} Teams Report",
            message=f"""
Dear Admin,

Attached is the {report_type} teams report you requested.

Best regards,
The Team
            """.strip(),
            attachment_content=base64.b64encode(content.encode()).decode(),
            attachment_filename=f"{report_type}_teams_report.csv"
        )
        
        email_sent = send_email_with_attachment(email_request)
        if not email_sent:
            logging.error(f"Failed to send report email to {email_account}")
            return jsonify({'error': 'Failed to send email with report'}), status.INTERNAL_SERVER_ERROR
           
        return jsonify({"content": "Report generated and sent successfully!"}), status.OK

    except ValidationError as e:
         return jsonify({'error': str(e)}), status.BAD_REQUEST
    except OperationFailure as e:
        logging.error("OperationFailure: %s", e)
        return jsonify({'error': 'Database operation failed due to an internal error.'}), status.INTERNAL_SERVER_ERROR

    except Exception as e:
        logging.error("Encountered exception: %s", e)
        return jsonify({'error': "Internal Server Error. Check server logs for details."}), status.INTERNAL_SERVER_ERROR

