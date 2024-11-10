# UA CTF Backend

This is the backend for the UA CTF (Capture The Flag) application. It's built using Flask and MongoDB.

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/CS-495-FALL-2024-TEAM-2/uactf-backend.git
   cd uactf-backend
   ```

2. Install the required packages:
   ```
   python -m pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   cd api
   ```

   You have two options for setting up the environment variables:

   a. Copy the `.env` file provided in the Slack channel into the `api` folder.

   OR

   b. Set the environment variables manually:
   ##
   For Unix-based systems (Linux, macOS):
   ```
   export DB_USERNAME=your_username
   export DB_PASSWORD=your_password
   export CLIENT_ORIGIN=client_origin
   export SECRET_KEY=<secret_key>
   ```

   For Windows:
   ```
   set DB_USERNAME=your_username
   set DB_PASSWORD=your_password
   set CLIENT_ORIGIN=client_origin
   set SECRET_KEY=<secret_key
   ```

   To generate the secret key you can run:
    ```
   import secrets
   secret_key = secrets.token_urlsafe(64)
   print(secret_key)
   ```


   Replace `your_username` and `your_password` with your MongoDB Atlas credentials. Replace `client_origin` with the origin of your client.

## Running the Application

To run the application, use the following command:

```
flask run
```

By default, this will start the server on `http://127.0.0.1:5000/`.

## API Endpoints

This API uses role-based access control (RBAC) to limit access to certain endpoints based on the user’s role. The following roles are supported:

- **admin**: Has the highest level of access, including creating and updating competitions and creating challenges.
- **crimson_defense**: Can create challenges.
- **teacher**: Can view challenges and retrieve current competitions.

### Authentication
All role-protected routes require a valid `access_token` cookie. Tokens are obtained via the `/auth/login` endpoint. If the access token expires, the API will attempt to refresh it using a valid `refresh_token`.

### Roles and Endpoint Access

| Endpoint                     | Method | Allowed Roles       | Description                                                                 |
|------------------------------|--------|---------------------|-----------------------------------------------------------------------------|
| `/auth/login`                | POST   | Public             | Authenticates a user and returns an `access_token` and `refresh_token`.     |
| `/challenges/create`         | POST   | `admin`, `crimson_defense` | Creates a new challenge with required details specified in JSON.            |
| `/challenges/get`            | GET    | `teacher`          | Retrieves a list of challenges.                                             |
| `/competitions/create`       | POST   | `admin`            | Creates a new competition with details such as name, deadline, and status.  |
| `/competitions/get`          | GET    | `admin`             | Retrieves all competitions.                                                 |
| `/competitions/get/current`  | GET    | `teacher`          | Retrieves currently active competitions.                                    |
| `/competitions/update/<id>`  | POST   | `admin`            | Updates a competition (e.g., change active status) by ID.                   |

### Request Payload Schemas

The API expects specific JSON payloads for certain endpoints. Below are the schemas defined for each of these payloads.

#### `CreateChallengeRequest`
Used in the `/challenges/create` endpoint.

```json
{
  "challenge_name": "string",
  "points": 100,
  "creator_name": "string",
  "division": [1, 2],
  "challenge_description": "string",
  "flag": "string",
  "is_flag_case_sensitive": true,
  "challenge_category": "string",
  "verified": true,
  "solution_explanation": "string",
  "hints": [
    {
      "hint": "string",
      "point_cost": 10
    }
  ]
}
```

#### `CreateCompetitionRequest`
Used in the `/competitions/create` endpoint.

```json
{
  "competition_name": "string",
  "registration_deadline": "2024-12-31T23:59:59",
  "is_active": true
}
```


### Example Usage

Here are some examples of `curl` requests for the protected endpoints.

1. **Create a Challenge** (Requires `admin` or `crimson_defense` role)

    ```bash
    curl -X POST http://127.0.0.1:5000/challenges/create \
         -H "Content-Type: application/json" \
         -H "Cookie: access_token=<crimson_defense_access_token>" \
         -d '{
               "challenge_name": "New Challenge",
               "points": 100,
               "creator_name": "John Doe",
               "division": [1, 2],
               "challenge_description": "This is a test challenge",
               "flag": "FLAG{test_flag}",
               "is_flag_case_sensitive": true,
               "challenge_category": "Forensics",
               "verified": true,
               "solution_explanation": "This is how you solve it",
               "hints": [{"hint": "Try harder!", "point_cost": 5}]
             }'
    ```

2. **Create a Competition** (Requires `admin` role)

    ```bash
    curl -X POST http://127.0.0.1:5000/competitions/create \
         -H "Content-Type: application/json" \
         -H "Cookie: access_token=<admin_access_token>" \
         -d '{
               "competition_name": "Winter Coding Competition",
               "registration_deadline": "2024-12-31T23:59:59",
               "is_active": true
             }'
    ```

3. **Get Current Competitions** (Requires `teacher` role)

    ```bash
    curl -X GET http://127.0.0.1:5000/competitions/get/current \
         -H "Cookie: access_token=<teacher_access_token>"
    ```

Replace `<role_access_token>` with the actual access token for the respective role. Ensure that tokens are correctly generated and signed for the specified roles.

A Non-exhaustive list of endpoints:

1. **GET /**  
   - Returns a welcome message.

2. **GET /testdb**  
   - Tests the database connection.

3. **POST /challenges/create**  
   - Creates a new challenge.
   - Requires a JSON body with challenge details.

4. **GET /challenges/get**  
   - Retrieves all challenges in the database.
   - Optional parameter `year` to filter challenges from that year, e.g., `/challenges/get?year=2023`.

5. **GET /challenges/details**  
   - Fetches details of a specific challenge based on `challenge_id` parameter.
   - Note: Has been updated to accept only POST requests with required authentication.

6. **POST /auth/login**  
   - Authenticates user login with email and password.
   - Returns `access_token` and `refresh_token`, also set as HTTP-only cookies.

7. **GET /auth/role**  
   - Returns the role of the logged-in user based on the `access_token`.
   - Requires a valid `access_token` cookie.

8. **POST /accounts/teachers/create**  
   - Creates a teacher account.
   - Requires a JSON body with teacher details (first name, last name, school name, contact number, etc.).

9. **GET /accounts/teachers/verify**  
   - Verifies a teacher’s login credentials via `email` and `password` query parameters.

10. **POST /accounts/crimson_defense/create**  
    - Creates a Crimson Defense account.
    - Requires a JSON body with email and other details.

11. **POST /accounts/admin/create**  
    - Creates an admin account.
    - Need to be logged in an admin
    - Requires a JSON body with admin details, including email.

12. **POST /competitions/create**  
    - Creates a new competition.
    - Requires a JSON body with competition details such as name, deadlines, and active status.

13. **GET /competitions/get**  
    - Retrieves all competitions stored in the database.

14. **GET /competitions/get/current**  
    - Retrieves active competitions with a valid registration deadline.

15. **GET /competitions/details**  
    - Returns details for a competition based on `competition_id` parameter.
    - Requires a valid `competition_id`.

16. **POST /competitions/update/<string:competition_id>**  
    - Updates details for a specific competition identified by `competition_id`.
    - Requires a JSON body with fields to update (e.g., `is_active`).

## File Structure

- `app.py`: Main application file containing the Flask routes and database connection logic.
- `models.py`: Contains the Pydantic model for challenge creation requests.
- `http_status_codes.py`: Contains HTTP status codes used in the application.
- `requirements.txt`: Lists all Python dependencies for the project.

## Environment Variables

- `DB_USERNAME`: MongoDB Atlas username
- `DB_PASSWORD`: MongoDB Atlas password
- `CLIENT_ORIGIN`: Frontend Domain, usually localhost:3000
- `SECRET_KEY`: Used for Auth tokens. You can generate one using the code in part 3 of the setup. We don't have or need a global secret key, because tokens are local.


These should be set either in the `.env` file in the `api` folder or as system environment variables.

## Error Handling

The application includes error handling for various scenarios, including database connection issues, validation errors, and operation failures. Errors are logged for debugging purposes.

## Dependencies

Major dependencies include:
- Flask: Web framework
- PyMongo: MongoDB driver
- python-dotenv: For loading environment variables
- Pydantic: For data validation
- Resend: For securely sending emails

For a complete list of dependencies, refer to the `requirements.txt` file.
