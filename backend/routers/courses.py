from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from backend.core.security import lecturer_only, get_current_user
from backend.db.database import get_db
from backend.models.course_models import CourseCreate, SessionCreate
from backend.services.qr_service import generate_qr_token, generate_qr_image_b64, verify_qr_token

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _id(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Create course ─────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_course(payload: CourseCreate, current_user: dict = Depends(lecturer_only)):
    db = get_db()

    existing = await db.courses.find_one({"course_code": payload.course_code.upper()})
    if existing:
        raise HTTPException(400, "Course code already exists")

    doc = {
        **payload.model_dump(),
        "course_code": payload.course_code.upper(),
        "lecturer_id": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.courses.insert_one(doc)
    return {"message": "Course created", "id": str(result.inserted_id)}


# ── Get my courses (lecturer) ─────────────────────────────────────────────────

@router.get("/my")
async def get_my_courses(current_user: dict = Depends(lecturer_only)):
    db = get_db()
    cursor = db.courses.find({"lecturer_id": current_user["user_id"]}).sort("created_at", -1)
    courses = []
    async for doc in cursor:
        _id(doc)
        courses.append(doc)
    return courses


# ── Get single course ─────────────────────────────────────────────────────────

@router.get("/{course_id}")
async def get_course(course_id: str, current_user: dict = Depends(lecturer_only)):
    db = get_db()
    doc = await db.courses.find_one({"_id": ObjectId(course_id), "lecturer_id": current_user["user_id"]})
    if not doc:
        raise HTTPException(404, "Course not found")
    return _id(doc)


# ── Delete course ─────────────────────────────────────────────────────────────

@router.delete("/{course_id}")
async def delete_course(course_id: str, current_user: dict = Depends(lecturer_only)):
    db = get_db()
    result = await db.courses.delete_one({"_id": ObjectId(course_id), "lecturer_id": current_user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Course not found")
    return {"message": "Course deleted"}


# ── Open attendance session ───────────────────────────────────────────────────

@router.post("/{course_id}/sessions", status_code=201)
async def open_session(
    course_id: str,
    payload: SessionCreate,
    current_user: dict = Depends(lecturer_only),
):
    db = get_db()
    lecturer_id = current_user["user_id"]

    # Verify course belongs to this lecturer
    course = await db.courses.find_one({"_id": ObjectId(course_id), "lecturer_id": lecturer_id})
    if not course:
        raise HTTPException(404, "Course not found")

    # Check no active session already open for this course
    active = await db.attendance_sessions.find_one({
        "course_id": course_id,
        "lecturer_id": lecturer_id,
        "status": "active",
    })
    if active:
        raise HTTPException(400, "An active session already exists for this course. Close it first.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=payload.duration_minutes)

    doc = {
        "course_id":        course_id,
        "course_code":      course["course_code"],
        "course_title":     course["course_title"],
        "lecturer_id":      lecturer_id,
        "latitude":         payload.latitude,
        "longitude":        payload.longitude,
        "radius_meters":    payload.radius_meters,
        "duration_minutes": payload.duration_minutes,
        "notes":            payload.notes,
        "status":           "active",
        "attendance_count": 0,
        "started_at":       now,
        "expires_at":       expires_at,
        "qr_token":         "",   # filled in after insert
    }

    result = await db.attendance_sessions.insert_one(doc)
    session_id = str(result.inserted_id)

    # Generate signed QR token
    qr_token = generate_qr_token(session_id)
    await db.attendance_sessions.update_one(
        {"_id": result.inserted_id},
        {"$set": {"qr_token": qr_token}},
    )

    # Generate QR image
    qr_url = f"/attend?token={qr_token}"
    qr_b64 = generate_qr_image_b64(qr_url)

    return {
        "message":    "Session opened",
        "session_id": session_id,
        "qr_token":   qr_token,
        "qr_image":   qr_b64,
        "expires_at": expires_at.isoformat(),
    }


# ── Get active sessions for lecturer ─────────────────────────────────────────

@router.get("/sessions/active")
async def get_active_sessions(current_user: dict = Depends(lecturer_only)):
    db = get_db()
    now = datetime.now(timezone.utc)

    # Auto-expire sessions past their time
    await db.attendance_sessions.update_many(
        {"lecturer_id": current_user["user_id"], "status": "active", "expires_at": {"$lt": now}},
        {"$set": {"status": "expired"}},
    )

    cursor = db.attendance_sessions.find({
        "lecturer_id": current_user["user_id"],
        "status": "active",
    }).sort("started_at", -1)

    sessions = []
    async for doc in cursor:
        _id(doc)
        sessions.append(doc)
    return sessions


# ── Get all sessions for a course ────────────────────────────────────────────

@router.get("/{course_id}/sessions")
async def get_course_sessions(course_id: str, current_user: dict = Depends(lecturer_only)):
    db = get_db()
    cursor = db.attendance_sessions.find({
        "course_id": course_id,
        "lecturer_id": current_user["user_id"],
    }).sort("started_at", -1)

    sessions = []
    async for doc in cursor:
        _id(doc)
        sessions.append(doc)
    return sessions


# ── Get session QR code ───────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/qr")
async def get_session_qr(session_id: str, current_user: dict = Depends(lecturer_only)):
    db = get_db()
    session = await db.attendance_sessions.find_one({
        "_id": ObjectId(session_id),
        "lecturer_id": current_user["user_id"],
    })
    if not session:
        raise HTTPException(404, "Session not found")

    qr_url = f"/attend?token={session['qr_token']}"
    qr_b64 = generate_qr_image_b64(qr_url)

    return {
        "qr_image":   qr_b64,
        "qr_token":   session["qr_token"],
        "expires_at": session["expires_at"].isoformat(),
        "status":     session["status"],
    }


# ── Close session ─────────────────────────────────────────────────────────────

@router.patch("/sessions/{session_id}/close")
async def close_session(session_id: str, current_user: dict = Depends(lecturer_only)):
    db = get_db()
    result = await db.attendance_sessions.update_one(
        {"_id": ObjectId(session_id), "lecturer_id": current_user["user_id"], "status": "active"},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Active session not found")
    return {"message": "Session closed"}


# ── Get session by QR token (public — used by student scanner) ───────────────

@router.get("/sessions/by-token/{token}")
async def get_session_by_token(token: str):
    db = get_db()
    session_id = verify_qr_token(token)
    if not session_id:
        raise HTTPException(400, "Invalid or tampered QR code")

    session = await db.attendance_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(404, "Session not found")

    # Auto-expire check
    now = datetime.now(timezone.utc)
    if session["status"] == "active" and session["expires_at"] < now:
        await db.attendance_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "expired"}},
        )
        session["status"] = "expired"
    return {
        "session_id":    session_id,
        "course_code":   session["course_code"],
        "course_title":  session["course_title"],
        "status":        session["status"],
        "expires_at":    session["expires_at"].isoformat(),
        "latitude":      session["latitude"],
        "longitude":     session["longitude"],
        "radius_meters": session["radius_meters"],
    }