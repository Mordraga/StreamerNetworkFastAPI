from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import initialize_db
from routers import contacts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts.router)
initialize_db()