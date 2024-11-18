import datetime
import os
import jwt

secret_key = os.getenv("SECRET_KEY")
auth_algorithm = os.getenv("AUTH_ALGORITHM")

def generate_access_token(userId, role):
    try:
        access_token = jwt.encode(
            {
                "userId": userId,
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
                "iat": datetime.datetime.now(datetime.timezone.utc),
                "role": role,
            },
            secret_key,
            auth_algorithm
        )
        return access_token
    except Exception as e:
        return None

def generate_tokens(userId, role):
    try:
        access_token = generate_access_token(userId, role)
        refresh_token = jwt.encode(
            {
                "userId": userId,
                "role": role,
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
                "iat": datetime.datetime.now(datetime.timezone.utc),
            },
            secret_key,
            auth_algorithm
        )
        return access_token, refresh_token
    except Exception as e:
        return None
