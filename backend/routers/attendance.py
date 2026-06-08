from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timezone

from backend.core.security import student_only, get_current_user
from backend.db.database import get_db
from backend.services.geofence_service import check_geofence
from backend.services.face_service import encode_face_from_base64, compare_faces
from backend.services.liveness_service import check_liveness_from_b64
from backend.services.qr_service import verify_qr_token

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class MarkAttendanceRequest(BaseModel):
    token: str
    latitude: float  = Field(..., ge=-90,  le=90)
    longitude: float = Field(..., ge=-180, le=180)
    image_b64: str
    liveness_confirmed: bool = False
    device_id: str = ""


@router.post("/mark")
async def mark_attendance(
    payload: MarkAttendanceRequest,
    current_user: dict = Depends(student_only),
):
    db = get_db()
    student_id = current_user["user_id"]
    now = datetime.now(timezone.utc)

    # ── 1. Verify QR token ────────────────────────────────────────────────────
    session_id = verify_qr_token(payload.token)
    if not session_id:
        raise HTTPException(400, "Invalid or tampered QR code")

    session = await db.attendance_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(404, "Session not found")

    if session["status"] != "active":
        raise HTTPException(400, f"Session is {session['status']} — attendance cannot be marked")

    if session["expires_at"].replace(tzinfo=timezone.utc) < now:
        await db.attendance_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"status": "expired"}},
        )
        raise HTTPException(400, "Session has expired")

    # ── 2. Check geofence ─────────────────────────────────────────────────────
    geo = check_geofence(
        student_lat=payload.latitude,
        student_lon=payload.longitude,
        session_lat=session["latitude"],
        session_lon=session["longitude"],
        radius_meters=session["radius_meters"],
    )
    if not geo["inside"]:
        raise HTTPException(400, f"Outside attendance zone — {geo['message']}")

    # ── 3. Device tracking check ──────────────────────────────────────────────
    if payload.device_id:
        existing_device = await db.device_logs.find_one({
            "device_id": payload.device_id,
            "session_id": session_id,
        })
        if existing_device and existing_device["student_id"] != student_id:
            raise HTTPException(
                400,
                "This device has already been used to mark attendance for another "
                "student in this session. Proxy attendance is not allowed."
            )

    # ── 4. Liveness check ─────────────────────────────────────────────────────
    liveness = check_liveness_from_b64(payload.image_b64)
    if not liveness["live"]:
        raise HTTPException(400, f"Liveness check failed — {liveness['reason']}")

    # ── 5. Check face registered ──────────────────────────────────────────────
    face_record = await db.face_encodings.find_one({"student_id": student_id})
    if not face_record:
        raise HTTPException(400, "No face registered. Please register your face first.")

    # ── 6. Verify face ────────────────────────────────────────────────────────
    live_encoding = encode_face_from_base64(payload.image_b64)
    if live_encoding is None:
        raise HTTPException(400, "No face detected in the captured image. Please try again.")

    face_result = compare_faces(face_record["encoding"], live_encoding)
    if not face_result["matched"]:
        raise HTTPException(
            400,
            f"Face not recognised (confidence: {face_result['confidence']}%). "
            "Please ensure good lighting and face the camera directly."
        )

    # ── 7. Check duplicate attendance ─────────────────────────────────────────
    existing = await db.attendance_records.find_one({
        "student_id": student_id,
        "session_id": session_id,
    })
    if existing:
        raise HTTPException(400, "Attendance already marked for this session")

    # ── 8. Log device ─────────────────────────────────────────────────────────
    if payload.device_id:
        await db.device_logs.update_one(
            {"device_id": payload.device_id, "session_id": session_id},
            {
                "$set": {
                    "device_id":  payload.device_id,
                    "session_id": session_id,
                    "student_id": student_id,
                    "ip_address": "",
                    "marked_at":  now,
                },
            },
            upsert=True,
        )

    # ── 9. Record attendance ──────────────────────────────────────────────────
    student = await db.students.find_one({"_id": ObjectId(student_id)})

    record = {
        "student_id":          student_id,
        "session_id":          session_id,
        "course_id":           session["course_id"],
        "course_code":         session["course_code"],
        "course_title":        session["course_title"],
        "student_name":        student["full_name"] if student else "Unknown",
        "matric_number":       student["matric_number"] if student else "Unknown",
        "latitude":            payload.latitude,
        "longitude":           payload.longitude,
        "distance_m":          geo["distance"],
        "face_confidence":     face_result["confidence"],
        "liveness_confidence": liveness["confidence"],
        "device_id":           payload.device_id,
        "marked_at":           now,
    }

    await db.attendance_records.insert_one(record)

    await db.attendance_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$inc": {"attendance_count": 1}},
    )

    return {
        "message":             "Attendance marked successfully",
        "course_code":         session["course_code"],
        "course_title":        session["course_title"],
        "marked_at":           now.isoformat(),
        "distance_m":          geo["distance"],
        "face_confidence":     face_result["confidence"],
        "liveness_confidence": liveness["confidence"],
    }


@router.get("/session/{session_id}")
async def get_session_records(session_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.attendance_records.find(
        {"session_id": session_id}
    ).sort("marked_at", -1)
    records = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        records.append(doc)
    return records


@router.get("/my")
async def get_my_attendance(current_user: dict = Depends(student_only)):
    db = get_db()
    cursor = db.attendance_records.find(
        {"student_id": current_user["user_id"]}
    ).sort("marked_at", -1)
    records = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        records.append(doc)
    return records