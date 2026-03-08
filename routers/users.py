from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from routers.contacts import get_current_user

router = APIRouter()

class PreferencesUpdate(BaseModel):
    onboardingDismissed: Optional[bool] = None
    theme: Optional[str] = None
    timezone: Optional[str] = None
    displayNameOverride: Optional[str] = None
    timeFormat: Optional[str] = None

@router.get("/user/preferences")
async def get_preferences(user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM user_preferences WHERE user_id = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            "onboardingDismissed": False,
            "theme": "dark",
            "timezone": None,
            "displayNameOverride": None,
            "timeFormat": "12"
        }
    return {
        "onboardingDismissed": row["onboarding_dismissed"],
        "theme": row["theme"],
        "timezone": row["timezone"],
        "displayNameOverride": row["display_name_override"],
        "timeFormat": row["time_format"]
    }

@router.patch("/user/preferences")
async def update_preferences(prefs: PreferencesUpdate, user_id: str = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_preferences (user_id, onboarding_dismissed, theme, timezone, display_name_override, time_format)
        VALUES (%s, %s, COALESCE(%s, 'dark'), %s, %s, COALESCE(%s, '12'))
        ON CONFLICT (user_id) DO UPDATE SET
            onboarding_dismissed = COALESCE(EXCLUDED.onboarding_dismissed, user_preferences.onboarding_dismissed),
            theme = COALESCE(EXCLUDED.theme, user_preferences.theme),
            timezone = COALESCE(EXCLUDED.timezone, user_preferences.timezone),
            display_name_override = COALESCE(EXCLUDED.display_name_override, user_preferences.display_name_override),
            time_format = COALESCE(EXCLUDED.time_format, user_preferences.time_format)
        """,
        (
            user_id,
            prefs.onboardingDismissed,
            prefs.theme,
            prefs.timezone,
            prefs.displayNameOverride,
            prefs.timeFormat
        )
    )
    conn.commit()
    conn.close()
    return {"ok": True}