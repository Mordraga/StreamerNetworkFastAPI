from pydantic import BaseModel
from typing import Optional

class Contact(BaseModel):
    name: str
    relationship: Optional[str] = None
    keywords: Optional[list] = []
    links: Optional[list] = []
    availability: Optional[dict] = None