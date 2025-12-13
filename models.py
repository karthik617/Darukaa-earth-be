from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP, Date, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(128), unique=True, index=True, nullable=False)  # token id
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    sites = relationship("Site", back_populates="project", cascade="all, delete-orphan")

class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="sites")
    metrics = relationship("SiteMetric", back_populates="site", cascade="all, delete-orphan")

class SiteMetric(Base):
    __tablename__ = "site_metrics"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    metric_date = Column(Date, nullable=False)
    metric_type = Column(String(64), nullable=False)
    metric_value = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    site = relationship("Site", back_populates="metrics")