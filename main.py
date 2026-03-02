from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import initialize_db
from routers import contacts, auth

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mootskeeper.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
initialize_db()