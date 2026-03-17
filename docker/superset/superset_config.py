import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me")
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset.db"

# Connect to the local Postgres data warehouse
SQLALCHEMY_EXAMPLES_URI = "postgresql://postgres:postgres@dw-postgres:5432/data_warehouse"
