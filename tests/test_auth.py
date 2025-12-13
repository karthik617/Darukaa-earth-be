# backend/tests/test_auth.py
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ensure import from app package
from main import app
from database import Base, get_db
from app import models

# Create a temporary sqlite DB for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def create_test_db():
    # create tables
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_login_refresh_logout_flow():
    client = TestClient(app)

    # register
    r = client.post("/auth/register", json={"email": "karthik@test.com", "password": "Password123!"})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "karthik@test.com"

    # login (obtain access + refresh)
    r = client.post("/auth/login", data={"username": "karthik@test.com", "password": "Password123!"})
    assert r.status_code == 200
    login_data = r.json()
    assert "access_token" in login_data and "refresh_token" in login_data
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # use refresh endpoint to rotate tokens
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    refreshed = r.json()
    assert "access_token" in refreshed and "refresh_token" in refreshed
    new_refresh = refreshed["refresh_token"]

    # old refresh should now be revoked; calling refresh with old should fail
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401

    # logout (revoke current refresh)
    r = client.post("/auth/logout", json={"refresh_token": new_refresh})
    assert r.status_code == 204

    # using the revoked refresh should fail
    r = client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert r.status_code == 401
