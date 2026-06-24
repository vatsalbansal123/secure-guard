import os

from sqlalchemy import create_engine

# DB connection settings come from the environment, never hardcoded (closes
# INSECURE_DEFAULTS #6 and Bandit B105). See .env.example for the variable names.
SERVER = os.getenv("DB_SERVER", "")
DATABASE = os.getenv("DB_NAME", "")
USERNAME = os.getenv("DB_USER", "")
PASSWORD = os.getenv("DB_PASSWORD", "")

connection_string = (
    f"mssql+pyodbc://{USERNAME}:{PASSWORD}"
    f"@{SERVER}:1433/{DATABASE}"
    f"?driver=ODBC+Driver+18+for+SQL+Server"
    f"&encrypt=yes&trustServerCertificate=no"
)

engine = create_engine(connection_string)
