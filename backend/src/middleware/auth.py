"""Firebase ID token verification for protected API endpoints."""

import logging

import firebase_admin
from fastapi import HTTPException, Request
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (uses Application Default Credentials in Cloud Run)
if not firebase_admin._apps:
    firebase_admin.initialize_app()


async def verify_firebase_token(request: Request) -> dict:
    """FastAPI dependency that validates a Firebase ID token from the Authorization header.

    Returns the decoded token dict (contains uid, email, etc.).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.removeprefix("Bearer ")
    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception:
        logger.debug("Firebase token verification failed", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
