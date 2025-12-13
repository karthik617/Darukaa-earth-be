# backend/seed_data.py
import os
import json
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
import geospatial
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, mapping
from passlib.context import CryptContext

pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    # create user
    existing = db.query(models.User).filter(models.User.email == "admin@demo.com").one_or_none()
    if not existing:
        user = models.User(email="admin@demo.com", password_hash=pwd.hash("Password123!"))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user = existing

    # create project
    proj = geospatial.create_project(db, name="Demo Project", description="Seeded demo project", owner_id=user.id)

    # create two polygons (small squares)
    poly1 = Polygon([(78.0, 10.0), (78.01, 10.0), (78.01, 10.01), (78.0, 10.01), (78.0, 10.0)])
    poly2 = Polygon([(77.5, 9.5), (77.6, 9.5), (77.6, 9.6), (77.5, 9.6), (77.5, 9.5)])

    site1 = models.Site(project_id=proj.id, name="Demo Site 1", description="Small square", geom=from_shape(poly1, srid=4326))
    site2 = models.Site(project_id=proj.id, name="Demo Site 2", description="Another square", geom=from_shape(poly2, srid=4326))
    db.add_all([site1, site2])
    db.commit()
    print("Seeded: user admin@demo.com (Password123!), demo project, 2 sites.")
    db.close()

if __name__ == "__main__":
    seed()
