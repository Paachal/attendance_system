from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timezone

from backend.core.security import student_only
from backend.db.database import get_db
from backend.services.geofence_service import check_geofence
from backend.services.qr_service import verify_qr_token

router = APIRouter(prefix="/api/geofence", tags=["geofence"])


class GeofenceCheckRequest(BaseModel):
    latitude: float  = Field(..., ge=-90,  le=90)
    longitude: float = Field(..., ge=-180, le=180)
    session_id: str


class GeofenceTokenRequest(BaseModel):
    latitude:  float = Field(..., ge=-90,  le=90)
    longitude: float = Field(..., ge=-180, le=180)
    token: str  # QR token


# ── Check by session ID ───────────────────────────────────────────────────────

@router.post("/check")
async def check_location(
    payload: GeofenceCheckRequest,
    current_user: dict = Depends(student_only),
):
    """
    Student sends their GPS coordinates + session ID.
    Returns whether they are inside the geofence.
    """
    db = get_db()

    session = await db.attendance_sessions.find_one(
        {"_id": ObjectId(payload.session_id)}
    )
    if not session:
        raise HTTPException(404, "Session not found")

    # Check session is still active
    now = datetime.now(timezone.utc)
    if session["status"] != "active":
        raise HTTPException(400, f"Session is {session['status']} — attendance cannot be marked")
    if session["expires_at"].replace(tzinfo=None) < datetime.utcnow():
        await db.attendance_sessions.update_one(
            {"_id": ObjectId(payload.session_id)},
            {"$set": {"status": "expired"}},
        )
        raise HTTPException(400, "Session has expired")

    result = check_geofence(
        student_lat=payload.latitude,
        student_lon=payload.longitude,
        session_lat=session["latitude"],
        session_lon=session["longitude"],
        radius_meters=session["radius_meters"],
    )

    return {
        **result,
        "session_id":   payload.session_id,
        "course_code":  session["course_code"],
        "course_title": session["course_title"],
    }


# ── Check by QR token (used during QR scan flow) ─────────────────────────────

@router.post("/check-by-token")
async def check_location_by_token(
    payload: GeofenceTokenRequest,
    current_user: dict = Depends(student_only),
):
    """
    Student sends GPS + QR token. Verifies token, resolves session,
    then runs geofence check. Used in the Phase 7 combined flow.
    """
    db = get_db()

    session_id = verify_qr_token(payload.token)
    if not session_id:
        raise HTTPException(400, "Invalid or tampered QR code")

    session = await db.attendance_sessions.find_one(
        {"_id": ObjectId(session_id)}
    )
    if not session:
        raise HTTPException(404, "Session not found")

    now = datetime.now(timezone.utc)
    if session["status"] != "active":
        raise HTTPException(400, f"Session is {session['status']} — attendance cannot be marked")
    if session["expires_at"] < now:
        await db.attendance_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "expired"}},
        )
        raise HTTPException(400, "Session has expired")

    result = check_geofence(
        student_lat=payload.latitude,
        student_lon=payload.longitude,
        session_lat=session["latitude"],
        session_lon=session["longitude"],
        radius_meters=session["radius_meters"],
    )

    return {
        **result,
        "session_id":   session_id,
        "course_code":  session["course_code"],
        "course_title": session["course_title"],
    }