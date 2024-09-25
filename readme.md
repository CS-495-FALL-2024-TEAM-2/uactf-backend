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
   ```

   For Windows:
   ```
   set DB_USERNAME=your_username
   set DB_PASSWORD=your_password
   set CLIENT_ORIGIN=client_origin
   ```

   Replace `your_username` and `your_password` with your MongoDB Atlas credentials. Replace `client_origin` with the origin of your client.

## Running the Application

To run the application, use the following command:

```
flask run
```

By default, this will start the server on `http://127.0.0.1:5000/`.

## API Endpoints

1. **GET /**
   - Returns a welcome message.

2. **GET /testdb**
   - Tests the database connection.

3. **POST /challenges/create**
   - Creates a new challenge.
   - Requires a JSON body with challenge details.

4. **GET /challenges/get**
   - Gets all challenges in the database.
   - You can provide an optional parameter year to get all the challenges from that year. I.e. /challenges/get?=year

5. **GET /challenges/details**
   - Requires a parameter challenge_id to get the details for a challenge
   - Note: This endpoint will likely be updated to accept only post requests with authentication information required as part of the request
   - Returns all the challenges from that given year


## File Structure

- `app.py`: Main application file containing the Flask routes and database connection logic.
- `models.py`: Contains the Pydantic model for challenge creation requests.
- `http_status_codes.py`: Contains HTTP status codes used in the application.
- `requirements.txt`: Lists all Python dependencies for the project.

## Environment Variables

- `DB_USERNAME`: MongoDB Atlas username
- `DB_PASSWORD`: MongoDB Atlas password

These should be set either in the `.env` file in the `api` folder or as system environment variables.

## Error Handling

The application includes error handling for various scenarios, including database connection issues, validation errors, and operation failures. Errors are logged for debugging purposes.

## Dependencies

Major dependencies include:
- Flask: Web framework
- PyMongo: MongoDB driver
- python-dotenv: For loading environment variables
- Pydantic: For data validation

For a complete list of dependencies, refer to the `requirements.txt` file.
