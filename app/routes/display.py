import asyncio
import os
import httpx

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app.drawing import crop_drawing, read_items
from app.repositories.order_lookup import parse_barcode
from app.dependencies import scan_repo, employee_repo
from app.domain.derive_sessions import derive_sessions
from app.db import get_connection, _as_utc

router = APIRouter()

@router.get("/display")
async def display_page():
    return FileResponse("app/static/display.html")

@router.get("/api/stations/current")
async def current_state(token: str):

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT s.StationId, s.Name FROM dbo.StationDevice d "
            "JOIN dbo.Station s ON s.StationId = d.StationId "
            "WHERE d.DeviceToken = ? AND d.IsActive = 1",
            token,
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Unknown device token")

    station_id, station_name = row[0], row[1]

    now = datetime.now(timezone.utc)
    # returns a list of whoever is logged in
    employee_ids = await employee_repo.find_employee_at_device(token, now)

    employee_names = await employee_repo.find_employee_names(employee_ids)

    events = await scan_repo.list_events_for_device(token)
    sessions = derive_sessions(events)
    # open session means no end time yet
    open_session = next((s for s in sessions if s.status == "OPEN"), None)
    # scoped to open session instead of all time because we only care for THIS current ongoing session.
    start_at = open_session.started_at_utc if open_session else None
    flagged_at = None

    if open_session is not None:
        flagged_at = next(
            (e.received_at_utc for e in reversed(events)
            if e.event_type == "FLAG" and e.received_at_utc >= open_session.started_at_utc),
            None,
        )

    # to check whether or not a session is still running, feedback to verify that the scan landed.
    last_order = next(
        (e.order_ref for e in reversed(events) if e.event_type == "ORDER"),
        None,
    )
    # added short description aswell
    last_description = next(
            (e.description for e in reversed(events) if e.event_type == "ORDER"),
            None,
        )

    return {
        "server_now_utc": now,
        "station_id": station_id,
        "employee_ids": employee_ids,
        "employee_names": employee_names,
        "order_ref": open_session.order_ref if open_session else last_order,
        "description": last_description,
        "started_at_utc": start_at,
        "flagged_at_utc": flagged_at,
        "is_flagged": open_session.is_flagged if open_session else False,
        "is_running": open_session is not None,
        "station_name": station_name,
        "recent_durations": [
            s.duration_seconds
            for s in sessions
            if s.status == "CLOSED" and s.duration_seconds is not None
        ][-10:],
        # that takes the last ten, slicing past the end is safe in python
    }

async def _fetch_drawing_png(order_ref: str):
    """Shared by both drawing routes: validates the code, downloads the PNG
    from dalmenit, and returns (product number, PNG bytes).
    Pulled into one function so the two routes can't drift apart."""

    code = parse_barcode(order_ref)
    if code is None:
        raise HTTPException(status_code=404, detail="Not an order code")

    # Drop the quantity: 382-01309-239-1 -> 382-01309-239
    ref = f"{code.commande_id}-{code.produit_id}"
    url = os.environ["KPI_DRAWING_PAGE_URL"].format(ref=ref)

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            upstream = await client.get(url)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Drawing service unreachable")

    if upstream.status_code != 200:
        raise HTTPException(status_code=404, detail="No drawing for this order")

    if not upstream.headers.get("content-type", "").startswith("image/"):
        raise HTTPException(status_code=502, detail="Not an image")

    return int(code.produit_id), upstream.content


@router.get("/api/drawing/{order_ref}")
async def drawing(order_ref: str):
    """/api/drawing/382-01309-239-1  ->  the cropped drawing from
    http://dalmenit:8816/asm/382-01309-239"""

    # "_" is the convention for "a value I'm deliberately ignoring":
    # this route doesn't need the product number.
    _, png = await _fetch_drawing_png(order_ref)
    cropped = await asyncio.to_thread(crop_drawing, png)

    return Response(
        content=cropped,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"},
    )


# OCR results per drawing, kept in memory: "382-01309-239" -> [items].
# OCR takes a fraction of a second and the list for a product never changes,
# so each one is read once and remembered. Emptied when the server restarts,
# which is fine: it refills itself on the next scans.
_items_cache: dict[str, list[dict]] = {}


@router.get("/api/drawing/{order_ref}/items")
async def drawing_items(order_ref: str):
    """/api/drawing/382-01309-239-1/items  ->
    {"selected": 239, "items": [{"item": 239, "code": "F1", "width": 825, "height": 1384}, ...]}

    "selected" is the product that was scanned, so the display can highlight
    it the same way the drawing highlights it in orange."""

    code = parse_barcode(order_ref)
    if code is None:
        raise HTTPException(status_code=404, detail="Not an order code")
    ref = f"{code.commande_id}-{code.produit_id}"

    if ref in _items_cache:
        return {"selected": int(code.produit_id), "items": _items_cache[ref]}

    selected, png = await _fetch_drawing_png(order_ref)

    # OCR runs Tesseract as a separate program and waits for it, so it goes
    # on its own thread for the same reason as the crop: the server keeps
    # answering every other screen in the meantime.
    items = await asyncio.to_thread(read_items, png)

    # Only remember SUCCESSFUL reads. An empty result might be a one-off
    # glitch, and caching it would hide the list for that product until the
    # next restart.
    if items:
        _items_cache[ref] = items

    return {"selected": selected, "items": items}