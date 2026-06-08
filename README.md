# AttendX — Geo-Fenced Facial Recognition Attendance System

## Phase 1: Project Setup & Auth

### Project structure

```
attendance_system/
├── main.py                        # FastAPI app entry point
├── requirements.txt
├── .env.example                   # Copy to .env and fill in values
├── backend/
│   ├── core/
│   │   └── security.py           # JWT + password hashing
│   ├── db/
│   │   └── database.py           # MongoDB connection + indexes
│   ├── models/
│   │   └── user_models.py        # Pydantic schemas
│   └── routers/
│       └── auth.py               # /api/auth/* endpoints
└── frontend/
    ├── static/
    │   ├── css/style.css          # Global design system
    │   └── js/auth.js             # Token helpers + UI utils
    └── templates/
        ├── index.html             # Landing page
        ├── login.html             # Login (student + lecturer)
        ├── register.html          # Registration (student + lecturer)
        ├── lecturer_dashboard.html
        └── student_dashboard.html
```

---

## Setup

### 1. Prerequisites

- Python 3.10+
- MongoDB running locally on port 27017
  - Install: https://www.mongodb.com/docs/manual/installation/
  - Or use MongoDB Atlas (update MONGO_URI in .env)

### 2. Create virtual environment

```bash
cd attendance_system
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

> Note: `face-recognition` requires cmake and dlib.
> For Phase 1 only, you can skip it — it's only used from Phase 5 onwards.
> Install the rest first:

```bash
pip install fastapi uvicorn motor pymongo python-jose passlib python-multipart python-dotenv aiofiles
```

Full install (Phases 1–9):
```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — set a strong SECRET_KEY
```

### 5. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000

---

## API Endpoints (Phase 1)

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/student/register` | Register new student |
| POST | `/api/auth/student/login` | Student login → JWT |
| POST | `/api/auth/lecturer/register` | Register new lecturer |
| POST | `/api/auth/lecturer/login` | Lecturer login → JWT |
| GET  | `/api/auth/me/student` | Get current student profile |
| GET  | `/api/auth/me/lecturer` | Get current lecturer profile |
| GET  | `/health` | Health check |

Interactive API docs: http://localhost:8000/docs

---

## MongoDB Collections (Phase 1)

| Collection | Purpose |
|---|---|
| `students` | Student accounts |
| `lecturers` | Lecturer accounts |
| `courses` | Course catalogue (Phase 3) |
| `attendance_sessions` | Per-class sessions (Phase 3) |
| `attendance_records` | Individual attendance marks (Phase 7) |
| `face_encodings` | 128-d face vectors (Phase 2) |
| `device_logs` | Device fingerprint tracking (Phase 8) |

---

## Auth flow

```
Register → POST /api/auth/{role}/register
Login    → POST /api/auth/{role}/login → { access_token, role, name, user_id }
Store    → localStorage (att_token, att_role, att_name, att_user_id)
Use      → Authorization: Bearer <token>
Protect  → Depends(lecturer_only) or Depends(student_only)
```

---

## Phase build order

- [x] Phase 1 — Auth (this phase)
- [ ] Phase 2 — Face registration
- [ ] Phase 3 — Courses & session management
- [ ] Phase 4 — GPS geofencing
- [ ] Phase 5 — Live face verification
- [ ] Phase 6 — Liveness detection (MediaPipe)
- [ ] Phase 7 — QR scan → full pipeline
- [ ] Phase 8 — Device tracking
- [ ] Phase 9 — Dashboards & reports
