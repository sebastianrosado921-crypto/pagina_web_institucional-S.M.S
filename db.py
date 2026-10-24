import os
import psycopg2


def get_connection():
    """Conexión sencilla a PostgreSQL para el proyecto."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgresql://pagina_web_institucional_user:7lT3YqFnB8J53z3EKFHgGvRxnCBUxLhl@dpg-dbdv4o3ncjis73dk2tm0-a/pagina_web_institucional"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "22420653"),
        port=os.getenv("DB_PORT", "5432"),
    )
