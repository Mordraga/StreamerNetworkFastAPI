from fastapi import APIRouter, HTTPException, Request, Depends
from database import get_db
from models import Contact
import httpx
import json

router = APIRouter()

TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def get_current_user(request: Request) -> str:
    """Validate Google or Twitch bearer token and return stable user id."""
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with httpx.AsyncClient() as client:
        google_resp = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": auth})
        if google_resp.status_code == 200:
            google_data = google_resp.json()
            google_user = google_data.get("sub") or google_data.get("email")
            if google_user:
                return f"google:{google_user}"

        twitch_resp = await client.get(TWITCH_VALIDATE_URL, headers={"Authorization": auth})
        if twitch_resp.status_code == 200:
            twitch_login = twitch_resp.json().get("login")
            if twitch_login:
                return twitch_login

    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/contacts")
async def get_contacts(user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], **json.loads(row["data"])} for row in rows]


@router.post("/contacts")
async def add_contact(contact: Contact, user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contacts (user_id, data) VALUES (%s, %s)",
        (user_id, json.dumps(contact.model_dump()))
    )
    conn.commit()
    conn.close()
    return {"message": "Contact added"}


@router.put("/contacts/{contact_id}")
async def update_contact(contact_id: int, contact: Contact, user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE contacts SET data = %s WHERE id = %s AND user_id = %s",
        (json.dumps(contact.model_dump()), contact_id, user_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Contact updated"}


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: int, user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, user_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Contact deleted"}
