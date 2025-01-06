import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection details from .env
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_USER_PW"),
    "host": os.getenv("DB_IP"),
    "port": os.getenv("DB_PORT"),
}