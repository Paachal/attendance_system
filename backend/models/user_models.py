from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ── Shared ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: str


# ── Student ───────────────────────────────────────────────────────────────────

class StudentRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    matric_number: str = Field(..., min_length=4, max_length=20)
    department: str = Field(..., min_length=2, max_length=100)
    level: str = Field(..., pattern=r"^(100|200|300|400|500)$")


class StudentOut(BaseModel):
    id: str
    full_name: str
    email: str
    matric_number: str
    department: str
    level: str
    has_face: bool = False
    created_at: datetime


# ── Lecturer ──────────────────────────────────────────────────────────────────

class LecturerRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    staff_id: str = Field(..., min_length=3, max_length=20)
    department: str = Field(..., min_length=2, max_length=100)
    title: Optional[str] = Field(None, max_length=20)  # Dr., Prof., Mr., etc.


class LecturerOut(BaseModel):
    id: str
    full_name: str
    email: str
    staff_id: str
    department: str
    title: Optional[str]
    created_at: datetime
