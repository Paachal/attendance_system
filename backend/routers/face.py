from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from datetime import datetime, timezone
from bson import ObjectId

from backend.core.security import student_only
from backend.db.database import get_db
from backend.services.face_service import (
    encode_face_from_bytes,
    encode_face_from_base64,
    compare_faces,
    validate_image_bytes,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/register")
async def register_face(
    file: UploadFile = File(...),
    current_user: dict = Depends(student_only),
):
    db = get_db()
    student_id = current_user["user_id"]

    image_bytes = await file.read()
    error = validate_image_bytes(image_bytes)
    if error:
        raise HTTPException(400, error)

    encoding = encode_face_from_bytes(image_bytes)
    if encoding is None:
        raise HTTPException(
            400,
            "No face detected in the photo. Please upload a clear, well-lit photo "
            "showing your full face looking directly at the camera."
        )

    now = datetime.now(timezone.utc)

    await db.face_encodings.update_one(
        {"student_id": student_id},
        {
            "$set": {
                "student_id": student_id,
                "encoding": encoding,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    await db.students.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"has_face": True, "face_updated_at": now}},
    )

    return {"message": "Face registered successfully", "student_id": student_id}


@router.get("/status")
async def face_status(current_user: dict = Depends(student_only)):
    db = get_db()
    student_id = current_user["user_id"]

    record = await db.face_encodings.find_one(
        {"student_id": student_id},
        {"_id": 0, "student_id": 1, "updated_at": 1, "created_at": 1},
    )

    if not record:
        return {"has_face": False}

    return {
        "has_face": True,
        "registered_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


@router.delete("/register")
async def delete_face(current_user: dict = Depends(student_only)):
    db = get_db()
    student_id = current_user["user_id"]

    await db.face_encodings.delete_one({"student_id": student_id})
    await db.students.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"has_face": False}},
    )

    return {"message": "Face registration removed"}


class VerifyFaceRequest(BaseModel):
    image_b64: str


@router.post("/verify")
async def verify_face(
    payload: VerifyFaceRequest,
    current_user: dict = Depends(student_only),
):
    db = get_db()
    student_id = current_user["user_id"]

    record = await db.face_encodings.find_one({"student_id": student_id})
    if not record:
        raise HTTPException(400, "No face registered. Please register your face first.")

    live_encoding = encode_face_from_base64(payload.image_b64)
    if live_encoding is None:
        raise HTTPException(400, "No face detected in the captured image. Please try again.")

    result = compare_faces(record["encoding"], live_encoding)

    return {
        "matched":    result["matched"],
        "confidence": result["confidence"],
        "distance":   result["distance"],
        "message":    "Face verified" if result["matched"] else "Face not recognised",
    }