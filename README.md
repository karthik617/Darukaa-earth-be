# Darukaa.Earth – Backend (API)

## Overview

This backend powers the Darukaa.Earth geospatial analytics platform. It provides JWT-based authentication, project & site management, geospatial storage using PostGIS, and analytics APIs consumed by the React frontend.

The backend is built with **FastAPI**, **PostgreSQL + PostGIS**, and follows clean, scalable REST architecture suitable for production.

---

## Tech Stack

* **Framework**: FastAPI (Python)
* **Database**: PostgreSQL + PostGIS
* **ORM**: SQLAlchemy
* **Auth**: JWT (access + refresh tokens)
* **Geospatial**: GeoJSON + PostGIS geometry

---

## High-Level Architecture

```
Client (React)
   │
   │  JWT (Authorization: Bearer)
   ▼
FastAPI Backend
   ├── Auth (JWT, Users)
   ├── Projects
   ├── Sites (GeoJSON polygons)
   ├── Analytics (mocked / computed)
   ▼
PostgreSQL + PostGIS
```

---

## Database Schema (Simplified)

### users

* id (PK)
* email (unique)
* hashed_password
* created_at

### projects

* id (PK)
* name
* description
* owner_id (FK → users.id)
* created_at

### sites

* id (PK)
* project_id (FK → projects.id)
* name
* description
* geom (Geometry: Polygon)
* created_at

### site_analytics (mock / derived)

* site_id
* metric_date 
* metric_type 
* metric_value
* created_at

---

## Authentication Flow

1. User registers via `/auth/register`
2. User logs in via `/auth/login`
3. Backend returns **access token + refresh token**
4. Access token is required for all protected endpoints
5. Refresh token is used to rotate expired access tokens

---

## API Endpoints

### Auth

* `POST /auth/register` – Register new user
* `POST /auth/login` – Login & receive JWT
* `POST /auth/refresh` – Refresh access token

### Projects

* `POST /geo/projects` – Create project
* `GET /geo/projects` – List user projects
* `GET /geo/projects/{id}` – Project details

### Sites / Geospatial

* `POST /geo/projects/{project_id}/sites` – Add site (GeoJSON polygon)
* `GET /geo/projects/{project_id}/sites` – List sites as GeoJSON
* `GET /geo/sites/{id}` – Site details

### Analytics

* `GET /geo/sites/{id}/analytics?months=12` – Timeseries analytics

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repo-url>
cd Darukaa-earth-be
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

Create `.env`:

```
POSTGRES_USER=username
POSTGRES_PASSWORD=password
POSTGRES_HOST=hostname
POSTGRES_PORT=port
JWT_SECRET=super-secret-key
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7
```

### 5. Enable PostGIS

```sql
CREATE EXTENSION postgis;
```

### 6. Run Server

```bash
uvicorn main:app --reload
```

API available at: `http://localhost:8000`

---

## CI/CD (Backend)

* GitHub Actions runs:

  * Linting (flake8)
  * Formatting checks
  * Test execution
* Deployment can be configured on Render

---

## Notes

* Analytics data is mocked for demonstration
* Architecture supports replacing analytics with real pipelines later
* JWT security follows best practices

---
