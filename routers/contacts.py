from fastapi import APIRouter, HTTPException
from database import get_db
from models import Contact
import json

router = APIRouter()

# Hardcoded for now, replaced with real auth later
TEST_USER = "test_user"

@router.get("/contacts")
def get_contacts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE user_id = %s", (TEST_USER,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], **json.loads(row["data"])} for row in rows]

@router.post("/contacts")
def add_contact(contact: Contact):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contacts (user_id, data) VALUES (%s, %s)",
        (TEST_USER, json.dumps(contact.model_dump()))
    )
    conn.commit()
    conn.close()
    return {"message": "Contact added"}

@router.put("/contacts/{contact_id}")
def update_contact(contact_id: int, contact: Contact):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE contacts SET data = %s WHERE id = %s AND user_id = %s",
        (json.dumps(contact.model_dump()), contact_id, TEST_USER)
    )
    conn.commit()
    conn.close()
    return {"message": "Contact updated"}

@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM contacts WHERE id = %s AND user_id = %s",
        (contact_id, TEST_USER)
    )
    conn.commit()
    conn.close()
    return {"message": "Contact deleted"}