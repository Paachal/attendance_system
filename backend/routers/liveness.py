from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.core.security import student_only
from backend.services.liveness_service import check_liveness_from_b64

router = APIRouter(prefix="/api/liveness", tags=["liveness"])


class LivenessRequest(BaseModel):
    image_b64: str


@router.post("/check")
async def check_liveness(
    payload: LivenessRequest,
    current_user: dict = Depends(student_only),
):
    """
    Accepts a base64 webcam snapshot.
    Returns liveness result — whether it's a real person or a photo/spoof.
    """
    if not payload.image_b64:
        raise HTTPException(400, "No image provided")

    result = check_liveness_from_b64(payload.image_b64)

    if not result["live"]:
        raise HTTPException(400, result["reason"])

    return {
        "live":       result["live"],
        "confidence": result["confidence"],
        "message":    result["reason"],
    }