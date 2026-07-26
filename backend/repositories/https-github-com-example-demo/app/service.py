from app.database import get_connection


def run_service():
    return get_connection()
