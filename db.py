import os
import psycopg2

def get_connection():
    """Conexión a PostgreSQL para el proyecto paginaWeb_SMS."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "paginaWeb_SMS"),  # ✅ Nombre CORRECTO
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "22420653"),
        port=os.getenv("DB_PORT", "5432"),
    )
