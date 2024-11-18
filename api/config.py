import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_USERNAME = os.environ.get("DB_USERNAME")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_NAME = "crimsondefense_ctf"
    DB_CHALLENGES_COLLECTION = "challenges"
    DB_ACCOUNTS_COLLECTION = "accounts"
    DB_STUDENT_INFO_COLLECTION = "student_info"
    DB_TEACHER_INFO_COLLECTION = "teacher_info"
    DB_STUDENT_ACCOUNTS_COLLECTION = "student_accounts"
    DB_COMPETITION_COLLECTION = "competitions"
    DB_TEAMS_COLLECTION = "teams"
    DB_TEACHER_INFO_COLLECTION = "teacher_info"
    DB_STUDENT_INFO_COLLECTION = "student_info"
    DB_TEAM_ACCOUNTS_COLLECTION = "team_accounts"
    CLIENT_ORIGIN = os.environ.get("CLIENT_ORIGIN")
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    SENDER_EMAIL_ACCOUNT = os.environ.get("SENDER_EMAIL_ACCOUNT")


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    # TODO: change to test database


class ProdConfig(Config):
    DEBUG = False

config = {
    "dev": DevConfig,
    "test": TestConfig,
    "prod": ProdConfig
}
