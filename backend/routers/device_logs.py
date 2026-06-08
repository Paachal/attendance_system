from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from backend.core.security import lecturer_only
from backend.db.database import get_db

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("/session/{session_id}")
async def get_session_device_logs(
    session_id: str,
    current_user: dict = Depends(lecturer_only),
):
    """Returns all device logs for a session — lecturer only."""
    db = get_db()

    cursor = db.device_logs.find(
        {"session_id": session_id}
    ).sort("marked_at", -1)

    logs = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        logs.append(doc)

    return logs


@router.get("/flagged")
async def get_flagged_devices(current_user: dict = Depends(lecturer_only)):
    """
    Returns device IDs that appear more than once across different
    students in any session — potential proxy attendance.
    """
    db = get_db()

    pipeline = [
        {
            "$group": {
                "_id": {
                    "device_id":  "$device_id",
                    "session_id": "$session_id",
                },
                "student_count": {"$sum": 1},
                "students": {"$push": "$student_id"},
            }
        },
        {"$match": {"student_count": {"$gt": 1}}},
        {"$sort": {"student_count": -1}},
    ]

    flagged = []
    async for doc in db.device_logs.aggregate(pipeline):
        flagged.append({
            "device_id":     doc["_id"]["device_id"],
            "session_id":    doc["_id"]["session_id"],
            "student_count": doc["student_count"],
            "students":      doc["students"],
        })

    return flagged