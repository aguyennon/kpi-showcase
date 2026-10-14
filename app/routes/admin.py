import statistics
from datetime import datetime, timedelta, timezone
from itertools import groupby

from app import dependencies
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.auth import require_admin, verify_admin_login
from app.db import get_connection
from app.dependencies import scan_repo
from app.domain.derive_sessions import derive_sessions

router = APIRouter()

@router.get("/admin/login")
async def login_page():
    return FileResponse("app/static/admin_login.html")

@router.post("/admin/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not await verify_admin_login(username, password):
        return RedirectResponse("/admin/login?error=1", status_code=303)

    request.session.clear()
    request.session["admin"] = username
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/admin")
async def admin_page(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse("/admin/login", status_code=303)
    return FileResponse("app/static/admin.html")


def _lookup_names() -> tuple[dict[int, str], dict[int, str]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT StationId, Name FROM dbo.Station")
        stations = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT EmployeeId, Name FROM dbo.Employee")
        employees = {row[0]: row[1] for row in cursor.fetchall()}

    return stations, employees


def _summarise(sessions) -> dict:
    total = len(sessions)
    clean = [
        s.duration_seconds for s in sessions
        if s.status == "CLOSED" and not s.is_flagged and s.duration_seconds is not None
    ]

    def pct(count: int) -> float:
        return round(100 * count / total, 1) if total else 0.0

    return {
        "sessions": total,
        "clean": len(clean),
        "mean_seconds": round(statistics.mean(clean)) if clean else None,
        "median_seconds": round(statistics.median(clean)) if clean else None,
        "flagged_pct": pct(sum(s.is_flagged for s in sessions)),
        "autoclosed_pct": pct(sum(s.status == "AUTOCLOSED" for s in sessions)),
        "incomplete_pct": pct(sum(s.status == "INCOMPLETE" for s in sessions)),
        "open": sum(s.status == "OPEN" for s in sessions),
    }


@router.get("/api/admin/sessions", dependencies=[Depends(require_admin)])
async def admin_sessions(days: int = 7):
    days = max(1, min(days, 90))

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    events = await scan_repo.list_events_between(start - timedelta(hours=12), now)

    station_names, employee_names = _lookup_names()

    sessions = []

    for _token, group in groupby(events, key=lambda e: e.device_token):
        for s in derive_sessions(list(group)):
            if s.started_at_utc >= start:
                sessions.append(s)
    
    by_station = {}
    for s in sessions:
        by_station.setdefault(s.station_id, []).append(s)

    stations = [
        {"station_id": sid, "name": station_names.get(sid, str(sid)), **_summarise(group)}
        for sid, group in sorted(by_station.items())
    ]

    rows = [
        {
            "station": station_names.get(s.station_id, str(s.station_id)),
            "employee": employee_names.get(s.employee_id, "-") if s.employee_id else "-",
            "order_ref": s.order_ref,
            "description": s.description,
            "features": s.features.split(",") if s.features else [],
            "started_at_utc": s.started_at_utc,
            "ended_at_utc": s.ended_at_utc,
            "duration_seconds": s.duration_seconds,
            "status": s.status,
            "is_flagged": s.is_flagged,
        }
        for s in sorted(sessions, key=lambda s: s.started_at_utc, reverse=True)
    ]

    return {"days": days, "stations": stations, "sessions": rows}



