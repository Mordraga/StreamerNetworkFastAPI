import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://mootskeeper.com").rstrip("/")
REDIRECT_URI = f"{FRONTEND_URL}/callback"
GOOGLE_REDIRECT_URI = f"{FRONTEND_URL}/auth/google/callback"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HTTPException(status_code=503, detail=f"Missing required environment variable: {name}")
    return value


async def _resolve_google_user(auth_header: str) -> dict | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": auth_header})
    if resp.status_code != 200:
        return None

    user_data = resp.json()
    sub = user_data.get("sub")
    if not sub:
        return None
    return {
        "user_id": f"google:{sub}",
        "display_name": user_data.get("name", ""),
        "profile_image_url": user_data.get("picture", ""),
        "provider": "google",
    }


async def _resolve_twitch_user(auth_header: str) -> dict | None:
    twitch_client_id = os.environ.get("TWITCH_CLIENT_ID", "").strip()
    if not twitch_client_id:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        validate_resp = await client.get(TWITCH_VALIDATE_URL, headers={"Authorization": auth_header})
        if validate_resp.status_code != 200:
            return None
        login = validate_resp.json().get("login")
        if not login:
            return None

        user_resp = await client.get(
            f"https://api.twitch.tv/helix/users?login={login}",
            headers={
                "Authorization": auth_header,
                "Client-Id": twitch_client_id,
            },
        )
    if user_resp.status_code != 200:
        return None

    payload = user_resp.json()
    rows = payload.get("data") or []
    if not rows:
        return None
    user_data = rows[0]
    return {
        "user_id": login,
        "display_name": user_data.get("display_name", login),
        "profile_image_url": user_data.get("profile_image_url", ""),
        "provider": "twitch",
    }


async def _resolve_inkscout_supabase_user(auth_header: str) -> dict | None:
    supabase_url = os.environ.get("INKSCOUT_SUPABASE_URL", "").strip().rstrip("/")
    supabase_anon_key = os.environ.get("INKSCOUT_SUPABASE_ANON_KEY", "").strip()
    if not supabase_url or not supabase_anon_key:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "Authorization": auth_header,
                "apikey": supabase_anon_key,
            },
        )
    if resp.status_code != 200:
        return None

    data = resp.json()
    user_id = data.get("id")
    if not user_id:
        return None
    user_meta = data.get("user_metadata") or {}
    display_name = (
        user_meta.get("full_name")
        or user_meta.get("name")
        or data.get("email")
        or user_id
    )
    return {
        "user_id": f"inkscout:{user_id}",
        "display_name": display_name,
        "profile_image_url": user_meta.get("avatar_url", ""),
        "provider": "inkscout",
    }


async def resolve_user_from_auth_header(auth_header: str | None) -> dict:
    if not auth_header:
        raise HTTPException(status_code=401, detail="No token provided")

    # Provider order is intentional:
    # 1) InkScout Supabase (pseudo-SSO from InkScout)
    # 2) Google OAuth token
    # 3) Twitch OAuth token
    user = await _resolve_inkscout_supabase_user(auth_header)
    if user:
        return user

    user = await _resolve_google_user(auth_header)
    if user:
        return user

    user = await _resolve_twitch_user(auth_header)
    if user:
        return user

    raise HTTPException(status_code=401, detail="Invalid or expired token")


# Google OAuth endpoints
@router.get("/auth/google/login")
def google_login():
    """Redirect user to Google OAuth."""
    google_client_id = _require_env("GOOGLE_CLIENT_ID")
    params = (
        f"?client_id={google_client_id}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=email profile"
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth{params}")


@router.get("/auth/google/callback")
async def google_callback(code: str):
    """Exchange code for token, return as JSON."""
    google_client_id = _require_env("GOOGLE_CLIENT_ID")
    google_client_secret = _require_env("GOOGLE_CLIENT_SECRET")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    data = resp.json()
    return {"access_token": data["access_token"]}


@router.get("/auth/google/validate")
async def google_validate(request: Request):
    """Validate Google token and return user info."""
    auth_header = request.headers.get("Authorization")
    user = await _resolve_google_user(auth_header or "")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# Twitch OAuth endpoints
@router.get("/auth/login")
def login():
    """Redirect user to Twitch OAuth."""
    twitch_client_id = _require_env("TWITCH_CLIENT_ID")
    params = (
        f"?client_id={twitch_client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=user:read:email"
    )
    return RedirectResponse(TWITCH_AUTH_URL + params)


@router.get("/auth/callback")
async def callback(code: str):
    """Exchange code for token, return as JSON."""
    twitch_client_id = _require_env("TWITCH_CLIENT_ID")
    twitch_client_secret = _require_env("TWITCH_CLIENT_SECRET")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TWITCH_TOKEN_URL,
            params={
                "client_id": twitch_client_id,
                "client_secret": twitch_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")

    data = resp.json()
    return {"access_token": data["access_token"]}


@router.get("/auth/validate")
async def validate(request: Request):
    """
    Validate bearer token and return normalized user info.
    Supports InkScout (Supabase), Google, and Twitch tokens.
    """
    auth_header = request.headers.get("Authorization")
    return await resolve_user_from_auth_header(auth_header)

