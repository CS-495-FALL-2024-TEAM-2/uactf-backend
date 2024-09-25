import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_USERNAME = os.environ.get("DB_USERNAME")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_NAME = "crimsondefense_ctf"
    DB_CHALLENGES_COLLECTION = "challenges"
    CLIENT_ORIGIN = os.environ.get("CLIENT_ORIGIN")


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
