from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from backend.db.database import connect_db, disconnect_db
from backend.routers import auth, face, courses, geofence, attendance, liveness, device_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="Geo-Fenced Attendance System",
    description="Facial recognition + GPS attendance for higher institutions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(face.router)
app.include_router(courses.router)
app.include_router(geofence.router)
app.include_router(attendance.router)
app.include_router(liveness.router)
app.include_router(device_logs.router)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "frontend", "static")
if os.path.exists(static_dir):
    app.mount("/frontend/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(os.path.dirname(__file__), "frontend", "templates")

@app.get("/")
async def root():
    return FileResponse(os.path.join(templates_dir, "index.html"))

@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(templates_dir, "login.html"))

@app.get("/register")
async def register_page():
    return FileResponse(os.path.join(templates_dir, "register.html"))

@app.get("/dashboard/lecturer")
async def lecturer_dashboard():
    return FileResponse(os.path.join(templates_dir, "lecturer_dashboard.html"))

@app.get("/dashboard/student")
async def student_dashboard():
    return FileResponse(os.path.join(templates_dir, "student_dashboard.html"))

@app.get("/face/register")
async def face_register_page():
    return FileResponse(os.path.join(templates_dir, "face_register.html"))

@app.get("/courses")
async def courses_page():
    return FileResponse(os.path.join(templates_dir, "courses.html"))

@app.get("/session/{session_id}")
async def session_page(session_id: str):
    return FileResponse(os.path.join(templates_dir, "session.html"))

@app.get("/attend")
async def attend_page():
    return FileResponse(os.path.join(templates_dir, "attend.html"))

@app.get("/session-records")
async def session_records_page():
    return FileResponse(os.path.join(templates_dir, "session_records.html"))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "attendance-system"}