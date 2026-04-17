import os
import sys

from dotenv import load_dotenv

# Load .env from project root before any other imports that read env vars
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add project root to path so gmaps/config can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth_router, trips, cars, addresses, maps

app = FastAPI(title="Undriven API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://undriven.local",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(trips.router)
app.include_router(cars.router)
app.include_router(addresses.router)
app.include_router(maps.router)
