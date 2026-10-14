from datetime import datetime, timezone
from typing import Optional

from app.domain.types import ScanEvent, NewScanEvent
from app.db import get_connection, _as_utc


def _row_to_event(row) -> ScanEvent: # links a db row to scanevent dataclass
    return ScanEvent(
        id=row[0],
        station_id=row[1],
        device_token=row[2],
        raw_code=row[3],
        event_type=row[4],
        order_ref=row[5],
        reason_code=row[6],
        employee_id=row[7],
        received_at_utc=_as_utc(row[8]),
        client_reported_at_utc=_as_utc(row[9]),
        batch_no=row[10],
        description=row[11],
        features=row[12],

    )

_EVENT_COLUMNS = """ ScanEventId, StationId, DeviceToken, RawCode, EventType,
    OrderRef, ReasonCode, EmployeeId, ReceivedAtUtc, ClientReportedAtUtc, BatchNo, Description, Features """

class SqlScanRepository:
    async def record_scan(self, scan: NewScanEvent) -> ScanEvent:
        received = datetime.now(timezone.utc)

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO dbo.ScanEvent
                    (StationId, DeviceToken, RawCode, EventType,
                     OrderRef, ReasonCode, EmployeeId,
                     ReceivedAtUtc, ClientReportedAtUtc, BatchNo, 
                     Description, Features)
                OUTPUT INSERTED.ScanEventId
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                scan.station_id,
                scan.device_token,
                scan.raw_code,
                scan.event_type,
                scan.order_ref,
                scan.reason_code,
                scan.employee_id,
                received,
                scan.client_reported_at_utc,
                scan.batch_no,
                scan.description,
                scan.features,
            )

            new_id = cursor.fetchone()[0]
            conn.commit()

        return ScanEvent(
            id=new_id,
            station_id=scan.station_id,
            device_token=scan.device_token,
            raw_code=scan.raw_code,
            event_type=scan.event_type,
            order_ref=scan.order_ref,
            reason_code=scan.reason_code,
            employee_id=scan.employee_id,
            received_at_utc=received,
            client_reported_at_utc=scan.client_reported_at_utc,
            batch_no=scan.batch_no,
            description=scan.description,
            features=scan.features,
        )

    async def resolve_device(self, device_token: str) -> Optional[int]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT StationId FROM dbo.StationDevice "
                "WHERE DeviceToken = ? AND IsActive = 1",
                device_token,
            )
            row = cursor.fetchone()

        return row[0] if row else None

    async def list_events_for_station(self, station_id: int) -> list[ScanEvent]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_EVENT_COLUMNS} FROM dbo.ScanEvent "
                "WHERE StationId = ? "
                "ORDER BY ReceivedAtUtc, ScanEventId",
                station_id,
            )
            rows = cursor.fetchall()

        return [_row_to_event(row) for row in rows]
    

    async def list_events_for_device(self, device_token: str) -> list[ScanEvent]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_EVENT_COLUMNS} FROM dbo.ScanEvent "
                "WHERE DeviceToken = ? "
                "ORDER BY ReceivedAtUtc, ScanEventId",
                device_token,
            )
            rows = cursor.fetchall()

        return [_row_to_event(row) for row in rows]

    
    async def list_events_between(self, start_utc: datetime, end_utc: datetime) -> list:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_EVENT_COLUMNS} FROM dbo.ScanEvent "
                "WHERE ReceivedAtUtc >= ? AND ReceivedAtUtc < ? "
                "ORDER BY DeviceToken, ReceivedAtUtc, ScanEventId",
                start_utc,
                end_utc,
            )
            rows = cursor.fetchall()

        return [_row_to_event(row) for row in rows]

