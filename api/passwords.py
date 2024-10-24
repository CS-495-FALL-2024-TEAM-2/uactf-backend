import base64
import os
import bcrypt

def generate_password(length=12):
    password_bytes = os.urandom(length)
    password = base64.urlsafe_b64encode(password_bytes).decode('utf-8')[:length]
    return password

def bcrypt_hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')  # Return as a string

def bcrypt_verify_password(provided_password: str, stored_hashed_password: str) -> bool:
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hashed_password.encode('utf-8'))

