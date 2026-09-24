from app.db import get_connection

with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT StationId, Code, Name FROM dbo.Station")
    for row in cursor.fetchall():
        print(row)