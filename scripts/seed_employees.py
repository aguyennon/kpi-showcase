from app.db import get_connection
from app.domain.security import hash_pin

EMPLOYEES = [
    ("1001", "Test One", "1234"),
    ("1002", "Test Two", "5678"),
]

with get_connection() as conn:
    cursor = conn.cursor()

    for number, name, pin in EMPLOYEES:
        cursor.execute(
            "INSERT INTO dbo.Employee (EmployeeNumber, Name, PinHash) VALUES (?, ?, ?)",
            number, name, hash_pin(pin),
        )

    conn.commit()
    print(f"Seeded {len(EMPLOYEES)} employees")