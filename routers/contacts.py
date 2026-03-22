from fastapi import APIRouter, HTTPException, Request, Depends
from database import get_db
from models import Contact
import json
from routers.auth import resolve_user_from_auth_header

router = APIRouter()

async def get_current_user(request: Request) -> str:
    """Validate bearer token and return stable user id across providers."""
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await resolve_user_from_auth_header(auth)
    return user["user_id"]


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
