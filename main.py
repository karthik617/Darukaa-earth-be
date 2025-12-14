import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# import models
from auth import router as auth_router
from database import Base, engine
from geospatial import router as geo_router

IS_TESTING = os.getenv("PYTEST_RUNNING") == "1"

app = FastAPI(title="Darukaa.Earth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "https://darukaa-earth-fe.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    if IS_TESTING:
        return
    # Wait until Postgres is ready
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
            print("PostGIS enabled")
            break
        except OperationalError:
            print("Waiting for Postgres...")
            time.sleep(1)

    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Tables created!")


app.include_router(auth_router)
app.include_router(geo_router)


@app.get("/")
def index():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
