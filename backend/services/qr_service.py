import qrcode
import io
import base64
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")


def generate_qr_token(session_id: str) -> str:
    """
    Creates an HMAC-signed token for a session.
    Format: sessionid.signature
    """
    sig = hmac.new(
        SECRET_KEY.encode(),
        session_id.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    return f"{session_id}.{sig}"


def verify_qr_token(token: str) -> str | None:
    """
    Verifies the HMAC signature and returns the session_id,
    or None if invalid.
    """
    try:
        session_id, sig = token.rsplit(".", 1)
        expected = hmac.new(
            SECRET_KEY.encode(),
            session_id.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        if hmac.compare_digest(sig, expected):
            return session_id
        return None
    except Exception:
        return None


def generate_qr_image_b64(data: str) -> str:
    """
    Generates a QR code image from a string and returns it
    as a base64-encoded PNG string (for embedding in HTML).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")