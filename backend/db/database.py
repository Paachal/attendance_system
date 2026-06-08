from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "attendance_db")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI, tz_aware=True)
    db = client[DB_NAME]
    await create_indexes()
    print(f"Connected to MongoDB: {DB_NAME}")


async def disconnect_db():
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")


async def create_indexes():
    # students: unique email and matric number
    await db.students.create_index([("email", ASCENDING)], unique=True)
    await db.students.create_index([("matric_number", ASCENDING)], unique=True)

    # lecturers: unique email and staff ID
    await db.lecturers.create_index([("email", ASCENDING)], unique=True)
    await db.lecturers.create_index([("staff_id", ASCENDING)], unique=True)

    # courses: unique course code
    await db.courses.create_index([("course_code", ASCENDING)], unique=True)

    # attendance sessions: index on session status + course
    await db.attendance_sessions.create_index([("course_id", ASCENDING)])
    await db.attendance_sessions.create_index([("status", ASCENDING)])
    await db.attendance_sessions.create_index([("created_at", DESCENDING)])

    # attendance records: student + session (composite unique)
    await db.attendance_records.create_index(
        [("student_id", ASCENDING), ("session_id", ASCENDING)], unique=True
    )

    # device logs: device + session
    await db.device_logs.create_index([("device_id", ASCENDING), ("session_id", ASCENDING)])


def get_db():
    return db
