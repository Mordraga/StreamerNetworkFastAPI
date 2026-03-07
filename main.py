from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import initialize_db
from routers import contacts, auth, users

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mootskeeper.com", "https://www.mootskeeper.com", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(users.router)
initialize_db()