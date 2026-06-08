from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Course ────────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    course_code: str = Field(..., min_length=2, max_length=20)
    course_title: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=100)
    level: str = Field(..., pattern=r"^(100|200|300|400|500)$")
    semester: str = Field(..., pattern=r"^(first|second)$")
    units: int = Field(..., ge=1, le=6)


class CourseOut(BaseModel):
    id: str
    course_code: str
    course_title: str
    department: str
    level: str
    semester: str
    units: int
    lecturer_id: str
    created_at: datetime


# ── Attendance Session ────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    course_id: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(default=50.0, ge=10, le=500)
    duration_minutes: int = Field(default=60, ge=5, le=300)
    notes: Optional[str] = Field(None, max_length=200)


class SessionOut(BaseModel):
    id: str
    course_id: str
    course_code: str
    course_title: str
    lecturer_id: str
    latitude: float
    longitude: float
    radius_meters: float
    duration_minutes: int
    notes: Optional[str]
    status: str          # active | closed | expired
    qr_token: str
    attendance_count: int
    started_at: datetime
    expires_at: datetime