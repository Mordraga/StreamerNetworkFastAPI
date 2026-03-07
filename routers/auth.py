import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://mootskeeper.com")
REDIRECT_URI = f"{FRONTEND_URL}/callback"
GOOGLE_REDIRECT_URI = f"{FRONTEND_URL}/auth/google/callback"

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"

#Google OAuth endpoints
@router.get("/auth/google/login")
def google_login():
    """Redirect user to Google OAuth"""
    params = (
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=email profile"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth{params}")

@router.get("/auth/google/callback")
async def google_callback(code: str):
    """Exchange code for token, return as JSON"""
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    data = resp.json()
    return {"access_token": data["access_token"]}

@router.get("/auth/google/validate")
async def google_validate(request: Request):
    """Validate token and return user info"""
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="No token provided")

    async with httpx.AsyncClient() as client:
        resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": auth})

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = resp.json()
    return {
        "user_id": user_data["sub"],
        "display_name": user_data.get("name", ""),
        "profile_image_url": user_data.get("picture", "")
    }

# Twitch OAuth endpoints
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
    """Exchange code for token, return as JSON"""
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
    return {"access_token": data["access_token"]}


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

    login = resp.json()["login"]

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"https://api.twitch.tv/helix/users?login={login}",
            headers={
                "Authorization": auth,
                "Client-Id": TWITCH_CLIENT_ID
            }
        )

    user_data = user_resp.json()["data"][0]
    return {
        "user_id": login,
        "display_name": user_data["display_name"],
        "profile_image_url": user_data["profile_image_url"]
    }