# DriveIQ - Intelligent Vehicle Management Application

## Project Overview

An intelligent web application for vehicle management. Features include maintenance tracking, service reminders, mileage updates, and AI-powered consultation using the vehicle's owner manual.

## Tech Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with pgvector extension
- **AI**: OpenAI embeddings for semantic search

## Project Structure

```
4Runner/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # API route handlers
│   │   ├── core/      # Config, database setup
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   └── services/  # Business logic
│   └── requirements.txt
├── frontend/          # React application
│   ├── src/
│   │   ├── components/ # Reusable UI components
│   │   ├── pages/      # Page components
│   │   ├── services/   # API client
│   │   └── types/      # TypeScript interfaces
│   └── package.json
├── database/          # SQL migrations and seeds
│   └── init.sql       # Initial schema with pgvector
├── docs/              # Vehicle PDFs (manual, CARFAX)
└── scripts/           # Utility scripts
    └── ingest_documents.py  # PDF embedding ingestion
```

## Key APIs

- `GET/PATCH /api/vehicle` - Vehicle info and mileage updates
- `GET/POST/PATCH/DELETE /api/maintenance` - Maintenance records CRUD
- `GET/POST /api/reminders` - Service reminders with recurrence
- `POST /api/search` - Semantic search in documentation
- `POST /api/search/ask` - AI-powered Q&A about the vehicle

## Database Models

- **Vehicle**: VIN, make/model, mileage tracking
- **MaintenanceRecord**: Service history with costs
- **Reminder**: Date/mileage-based notifications with recurrence
- **DocumentChunk**: Vectorized PDF content for search

## Development Commands

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Database
docker-compose up -d postgres

# Ingest documents (requires OPENAI_API_KEY)
python scripts/ingest_documents.py
```

## Environment Variables

Required in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - For embeddings and chat
- `SECRET_KEY` - JWT signing key

## Vehicle Data

- VIN: JTEBU5JR2J5517128
- Year: 2018
- Make: Toyota
- Model: 4Runner
- Trim: SR5 Premium

## Coding Standards

- FastAPI with type hints and Pydantic validation
- React functional components with hooks
- TanStack Query for server state management
- Tailwind CSS for styling
- Follow existing patterns in the codebase
