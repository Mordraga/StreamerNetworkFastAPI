import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://mootskeeper.com")
REDIRECT_URI = f"{FRONTEND_URL}/callback"

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"


@router.get("/auth/login")
def login():
    """Redirect user to Twitch OAuth"""
    params = (
        f"?client_id={TWITCH_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=user:read:email"
    )
    return RedirectResponse(TWITCH_AUTH_URL + params)


@router.get("/auth/callback")
async def callback(code: str):
    """Exchange code for token, return to frontend with token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(TWITCH_TOKEN_URL, params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    data = resp.json()
    access_token = data["access_token"]

    # Redirect to frontend with token in URL fragment
    return RedirectResponse(f"{FRONTEND_URL}/#token={access_token}")


@router.get("/auth/validate")
async def validate(request: Request):
    """Validate token and return Twitch username"""
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="No token provided")

    async with httpx.AsyncClient() as client:
        resp = await client.get(TWITCH_VALIDATE_URL, headers={"Authorization": auth})

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    data = resp.json()
    return {"user_id": data["login"], "display_name": data["login"]}
