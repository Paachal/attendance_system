from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId

from backend.models.user_models import (
    StudentRegister, LecturerRegister,
    LoginRequest, TokenResponse,
    StudentOut, LecturerOut,
)
from backend.core.security import (
    hash_password, verify_password,
    create_access_token, get_current_user,
    lecturer_only, student_only,
)
from backend.db.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _serialize(doc: dict, id_field="_id") -> dict:
    """Convert MongoDB _id to string id."""
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Student Registration ──────────────────────────────────────────────────────

@router.post("/student/register", status_code=201)
async def register_student(payload: StudentRegister):
    db = get_db()

    # Check duplicates
    if await db.students.find_one({"email": payload.email}):
        raise HTTPException(400, "Email already registered")
    if await db.students.find_one({"matric_number": payload.matric_number}):
        raise HTTPException(400, "Matric number already registered")

    doc = {
        **payload.model_dump(),
        "password": hash_password(payload.password),
        "has_face": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.students.insert_one(doc)
    return {"message": "Student registered successfully", "id": str(result.inserted_id)}


# ── Student Login ─────────────────────────────────────────────────────────────

@router.post("/student/login", response_model=TokenResponse)
async def login_student(payload: LoginRequest):
    db = get_db()
    student = await db.students.find_one({"email": payload.email})
    if not student or not verify_password(payload.password, student["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(student["_id"]),
        "role": "student",
        "email": student["email"],
    })
    return TokenResponse(
        access_token=token,
        role="student",
        name=student["full_name"],
        user_id=str(student["_id"]),
    )


# ── Lecturer Registration ─────────────────────────────────────────────────────

@router.post("/lecturer/register", status_code=201)
async def register_lecturer(payload: LecturerRegister):
    db = get_db()

    if await db.lecturers.find_one({"email": payload.email}):
        raise HTTPException(400, "Email already registered")
    if await db.lecturers.find_one({"staff_id": payload.staff_id}):
        raise HTTPException(400, "Staff ID already registered")

    doc = {
        **payload.model_dump(),
        "password": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.lecturers.insert_one(doc)
    return {"message": "Lecturer registered successfully", "id": str(result.inserted_id)}


# ── Lecturer Login ────────────────────────────────────────────────────────────

@router.post("/lecturer/login", response_model=TokenResponse)
async def login_lecturer(payload: LoginRequest):
    db = get_db()
    lecturer = await db.lecturers.find_one({"email": payload.email})
    if not lecturer or not verify_password(payload.password, lecturer["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(lecturer["_id"]),
        "role": "lecturer",
        "email": lecturer["email"],
    })
    return TokenResponse(
        access_token=token,
        role="lecturer",
        name=lecturer["full_name"],
        user_id=str(lecturer["_id"]),
    )


# ── Profile endpoints ─────────────────────────────────────────────────────────

@router.get("/me/student", response_model=StudentOut)
async def get_student_profile(current_user: dict = Depends(student_only)):
    db = get_db()
    student = await db.students.find_one({"_id": ObjectId(current_user["user_id"])})
    if not student:
        raise HTTPException(404, "Student not found")
    return StudentOut(**_serialize(student))


@router.get("/me/lecturer", response_model=LecturerOut)
async def get_lecturer_profile(current_user: dict = Depends(lecturer_only)):
    db = get_db()
    lecturer = await db.lecturers.find_one({"_id": ObjectId(current_user["user_id"])})
    if not lecturer:
        raise HTTPException(404, "Lecturer not found")
    return LecturerOut(**_serialize(lecturer))
