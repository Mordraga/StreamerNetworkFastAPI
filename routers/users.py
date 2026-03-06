from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import get_db
from routers.contacts import get_current_user  # reuse the existing auth helper

router = APIRouter()

class PreferencesUpdate(BaseModel):
    onboardingDismissed: bool = False

@router.get("/user/preferences")
async def get_preferences(user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT onboarding_dismissed FROM user_preferences WHERE user_id = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return {"onboardingDismissed": row["onboarding_dismissed"] if row else False}

@router.patch("/user/preferences")
async def update_preferences(prefs: PreferencesUpdate, user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_preferences (user_id, onboarding_dismissed)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET onboarding_dismissed = EXCLUDED.onboarding_dismissed
        """,
        (user_id, prefs.onboardingDismissed)
    )
    conn.commit()
    conn.close()
    return {"ok": True}
