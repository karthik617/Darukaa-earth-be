from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    expires_in: Optional[int] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True

# Projects
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    class Config:
        orm_mode = True

class ProjectListItem(BaseModel):
    id: int
    name: str
    site_count: int

# Sites
class SiteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    geojson: dict

class SiteOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    class Config:
        orm_mode = True

class Feature(BaseModel):
    type: str
    properties: dict
    geometry: dict

class FeatureCollection(BaseModel):
    type: str
    features: List[Feature]

# Analytics
class TimeseriesPoint(BaseModel):
    date: date
    value: float

class SiteAnalytics(BaseModel):
    carbon: List[TimeseriesPoint]
    biodiversity_index: List[TimeseriesPoint]
