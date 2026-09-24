import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional

load_dotenv()

def _as_utc(value: Optional[datetime]) -> Optional[datetime]: # useful function to attach the right datetime to ssms
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc)

def get_connection() -> pyodbc.Connection:
    server = os.environ["KPI_DB_SERVER"]
    database = os.environ["KPI_DB_NAME"]
    driver = os.environ["KPI_DB_DRIVER"]
    user = os.environ["KPI_DB_USER"]
    password = os.environ["KPI_DB_PASSWORD"]

    return pyodbc.connect(
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
    )

