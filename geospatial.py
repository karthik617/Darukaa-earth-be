from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import shape
from sqlalchemy import func, text
import models
from datetime import date, timedelta
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models, schemas, auth
from jose import JWTError, jwt
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-dev-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

router = APIRouter(prefix="/geo", tags=["geo"])

def create_project(db: Session, name: str, description: str | None = None, owner_id: int | None = None):
    p = models.Project(name=name, description=description, owner_id=owner_id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def list_projects(db: Session,user_id: int):
    # return projects with site counts
    rows = db.query(models.Project.id, models.Project.name, func.count(models.Site.id).label("site_count")).outerjoin(models.Site,models.Site.project_id == models.Project.id).filter(models.Project.owner_id == user_id).group_by(models.Project.id,models.Project.name).all()
    return [{"id": r.id, "name": r.name, "site_count": r.site_count} for r in rows]

def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).one_or_none()

def create_site(db: Session, project_id: int, name: str, description: str, geojson: dict):
    geom = from_shape(shape(geojson["geometry"]), srid=4326)
    site = models.Site(project_id=project_id, name=name, description=description, geom=geom)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site

def list_sites_geojson(db: Session, project_id: int):
    q = db.query(models.Site.id, models.Site.name, models.Site.description, func.ST_AsGeoJSON(models.Site.geom).label("geojson")).filter(models.Site.project_id == project_id).all()
    features = []
    for r in q:
        features.append({
            "type": "Feature",
            "properties": {"id": r.id, "name": r.name, "description": r.description},
            "geometry": __parse_geojson_text(r.geojson)
        })
    return {"type": "FeatureCollection", "features": features}

def __parse_geojson_text(txt: str):
    import json
    return json.loads(txt)

def get_site(db: Session, site_id: int):
    r = db.query(models.Site, func.ST_AsGeoJSON(models.Site.geom).label("geojson")).filter(models.Site.id == site_id).one_or_none()
    if not r:
        return None
    site, geojson_text = r
    import json
    return {"id": site.id, "project_id": site.project_id, "name": site.name, "description": site.description, "geometry": json.loads(geojson_text)}

def site_area_ha(db: Session, site_id: int) -> float:
    q = db.query(
        func.ST_Area(func.Geography(models.Site.geom))
    ).filter(models.Site.id == site_id).scalar()
    if q is None:
        return 0.0
    # q is in m^2, convert to hectares
    return float(q) / 10000.0

def site_analytics_synthetic(db: Session, site_id: int, months: int = 12):
    area_ha = site_area_ha(db, site_id)
    import math
    today = date.today()
    carbon = []
    bio = []
    for i in range(months):
        dt = today - timedelta(days=30*(months - i - 1))
        # seasonal multiplier
        season = 1.0 + 0.2 * math.sin(2*math.pi*(i/12.0))
        carbon_value = area_ha * 0.5 / 12.0 * season  # very small synthetic number
        bio_value = 50.0 * season  # synthetic biodiversity index
        carbon.append({"date": dt.isoformat(), "value": round(carbon_value, 4)})
        bio.append({"date": dt.isoformat(), "value": round(bio_value, 2)})
    return {"carbon": carbon, "biodiversity_index": bio}

def get_current_user_from_header(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = db.query(models.User).filter(models.User.id == user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ---------- Projects ----------
@router.post("/projects", response_model=schemas.ProjectOut)
def _create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db), authorization: str = Header(None)):
    # require auth
    user = get_current_user_from_header(authorization, db)
    p = create_project(db, name=payload.name, description=payload.description, owner_id=user.id)
    return p

@router.get("/projects", response_model=list[schemas.ProjectListItem])
def _list_projects(db: Session = Depends(get_db), authorization: str = Header(None)):
    # require auth
    user = get_current_user_from_header(authorization, db)
    return list_projects(db,user.id)

@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def _get_project(project_id: int, db: Session = Depends(get_db), authorization: str = Header(None)):
    _ = get_current_user_from_header(authorization, db)
    p = get_project(db, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

# ---------- Sites ----------
@router.post("/projects/{project_id}/sites", response_model=schemas.SiteOut)
def _create_site(project_id: int, payload: schemas.SiteCreate, db: Session = Depends(get_db), authorization: str = Header(None)):
    
    _ = get_current_user_from_header(authorization, db)
    # verify project exists
    proj = get_project(db, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    site = create_site(db, project_id=project_id, name=payload.name, description=payload.description, geojson=payload.geojson)
    return site

@router.get("/projects/{project_id}/sites", response_model=schemas.FeatureCollection)
def list_sites(project_id: int, db: Session = Depends(get_db), authorization: str = Header(None)):
    _ = get_current_user_from_header(authorization, db)
    fc = list_sites_geojson(db, project_id)
    return fc

@router.get("/sites/{site_id}", response_model=schemas.SiteOut)
def _get_site(site_id: int, db: Session = Depends(get_db), authorization: str = Header(None)):
    _ = get_current_user_from_header(authorization, db)
    s = get_site(db, site_id)
    if not s:
        raise HTTPException(status_code=404, detail="Site not found")
    return s

@router.get("/sites/{site_id}/analytics", response_model=schemas.SiteAnalytics)
def site_analytics(site_id: int, months: int = 12, db: Session = Depends(get_db), authorization: str = Header(None)):
    _ = get_current_user_from_header(authorization, db)
    a = site_analytics_synthetic(db, site_id, months=months)
    return a