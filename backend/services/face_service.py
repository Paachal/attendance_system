import numpy as np
import base64
import io
import os
from PIL import Image
from typing import Optional


def _get_app():
    """
    Lazy-load InsightFace app.
    Downloads buffalo_sc model (~100MB, much lighter than TensorFlow).
    """
    import insightface
    from insightface.app import FaceAnalysis

    app = FaceAnalysis(
        name="buffalo_sc",
        root=os.environ.get("INSIGHTFACE_HOME", "/tmp/insightface"),
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=(320, 320))
    return app


_app = None

def get_app():
    global _app
    if _app is None:
        _app = _get_app()
    return _app


def encode_face_from_bytes(image_bytes: bytes) -> Optional[list]:
    """
    Extracts a 512-d face embedding using InsightFace.
    Returns a list for MongoDB storage, or None if no face found.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)

        app = get_app()
        faces = app.get(img_np)

        if not faces:
            return None

        # Use the largest face
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.embedding.tolist()

    except Exception as e:
        print(f"Face encoding error: {e}")
        return None


def encode_face_from_base64(b64_string: str) -> Optional[list]:
    """
    Accepts a base64-encoded image (with or without data URI prefix).
    Returns embedding list or None.
    """
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    image_bytes = base64.b64decode(b64_string)
    return encode_face_from_bytes(image_bytes)


def compare_faces(
    stored_encoding: list,
    live_encoding: list,
    threshold: float = 0.5,
) -> dict:
    """
    Compares two 512-d InsightFace embeddings using cosine similarity.
    Higher similarity = more similar. Threshold 0.5 works well for InsightFace.
    """
    stored_np = np.array(stored_encoding)
    live_np   = np.array(live_encoding)

    # Cosine similarity
    similarity = float(
        np.dot(stored_np, live_np) /
        (np.linalg.norm(stored_np) * np.linalg.norm(live_np) + 1e-10)
    )

    matched    = similarity >= threshold
    confidence = round(max(0.0, similarity * 100), 1)

    return {
        "matched":    matched,
        "distance":   round(1 - similarity, 4),
        "confidence": min(confidence, 100.0),
    }


def validate_image_bytes(image_bytes: bytes, max_mb: int = 5) -> str | None:
    """Returns an error string or None if image is valid."""
    if len(image_bytes) > max_mb * 1024 * 1024:
        return f"Image too large. Maximum size is {max_mb}MB."
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.format not in ("JPEG", "PNG", "WEBP"):
            return "Only JPEG, PNG, and WEBP images are supported."
    except Exception:
        return "Invalid image file."
    return None