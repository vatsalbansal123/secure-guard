from sqlalchemy import create_engine

SERVER = "your-server.database.windows.net"
DATABASE = "your-db"
USERNAME = "your-user"
PASSWORD = "your-password"

connection_string = (
    f"mssql+pyodbc://{USERNAME}:{PASSWORD}"
    f"@{SERVER}:1433/{DATABASE}"
    f"?driver=ODBC+Driver+18+for+SQL+Server"
    f"&encrypt=yes&trustServerCertificate=no"
)

engine = create_engine(connection_string)