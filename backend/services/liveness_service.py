import numpy as np
import base64
import io
from PIL import Image


# Load OpenCV face detector once at module level
import cv2
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
_eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)


def check_liveness_from_b64(b64_string: str) -> dict:
    """
    Liveness check using OpenCV Haar cascades.
    Checks:
    1. Face detected and large enough
    2. At least one eye detected (rules out printed side-profile photos)
    3. Image is not uniformly flat (texture check — rules out printed photos)
    """
    try:
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]

        image_bytes = base64.b64decode(b64_string)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        img_h, img_w = gray.shape

        # ── Check 1: Face detected ────────────────────────────────────────────
        faces = _face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
        )

        if len(faces) == 0:
            return {
                "live":       False,
                "reason":     "No face detected. Please face the camera in good lighting.",
                "confidence": 0.0,
            }

        # Use the largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        # ── Check 2: Face size ────────────────────────────────────────────────
        face_area_ratio = (w * h) / (img_w * img_h)
        if face_area_ratio < 0.05:
            return {
                "live":       False,
                "reason":     "Face too far from camera. Please move closer.",
                "confidence": 10.0,
            }

        # ── Check 3: Eye detection inside face region ─────────────────────────
        face_roi = gray[y:y+h, x:x+w]
        eyes = _eye_cascade.detectMultiScale(
            face_roi,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(20, 20),
        )

        if len(eyes) == 0:
            return {
                "live":       False,
                "reason":     "Eyes not detected. Please open your eyes and face the camera directly.",
                "confidence": 20.0,
            }

        # ── Check 4: Texture / gradient variance (anti-photo spoof) ──────────
        # A printed photo held up to camera has very low local gradient variance
        # A real face has high texture variation (skin pores, shadows, etc.)
        laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()

        if laplacian_var < 30:
            return {
                "live":       False,
                "reason":     "Image appears too flat or blurry. Please use a live camera.",
                "confidence": 25.0,
            }

        # ── All checks passed ─────────────────────────────────────────────────
        # Compute confidence from face size + eye count + texture score
        size_score    = min(face_area_ratio / 0.25, 1.0) * 35
        eye_score     = min(len(eyes) / 2, 1.0) * 30
        texture_score = min(laplacian_var / 200, 1.0) * 35
        confidence    = round(size_score + eye_score + texture_score, 1)

        return {
            "live":       True,
            "reason":     "Liveness confirmed",
            "confidence": min(confidence, 100.0),
        }

    except Exception as e:
        print(f"Liveness check error: {e}")
        return {
            "live":       False,
            "reason":     f"Liveness check error: {str(e)}",
            "confidence": 0.0,
        }