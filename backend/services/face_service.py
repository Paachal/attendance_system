import numpy as np
import base64
import io
from PIL import Image
from typing import Optional


def encode_face_from_bytes(image_bytes: bytes) -> Optional[list]:
    try:
        from deepface import DeepFace
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)

        embedding_objs = DeepFace.represent(
            img_path=img_np,
            model_name="Facenet",
            enforce_detection=True,
            detector_backend="opencv",
        )

        if not embedding_objs:
            return None

        return embedding_objs[0]["embedding"]

    except Exception as e:
        print(f"Face encoding error: {e}")
        return None


def encode_face_from_base64(b64_string: str) -> Optional[list]:
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    image_bytes = base64.b64decode(b64_string)
    return encode_face_from_bytes(image_bytes)


def compare_faces(stored_encoding: list, live_encoding: list, threshold: float = 10.0) -> dict:
    stored_np = np.array(stored_encoding)
    live_np   = np.array(live_encoding)
    distance  = float(np.linalg.norm(stored_np - live_np))
    matched   = distance <= threshold
    confidence = round(max(0.0, (1 - distance / 20) * 100), 1)
    return {
        "matched":    matched,
        "distance":   round(distance, 4),
        "confidence": min(confidence, 100.0),
    }


def validate_image_bytes(image_bytes: bytes, max_mb: int = 5) -> str | None:
    if len(image_bytes) > max_mb * 1024 * 1024:
        return f"Image too large. Maximum size is {max_mb}MB."
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.format not in ("JPEG", "PNG", "WEBP"):
            return "Only JPEG, PNG, and WEBP images are supported."
    except Exception:
        return "Invalid image file."
    return None