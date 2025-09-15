# Copilot Instructions for NutriScopeAI_v2

## Project Overview
NutriScopeAI_v2 is a modular Python application for nutritional data extraction, analysis, and reporting. It consists of a FastAPI backend and a NiceGUI-based frontend. The backend processes lab reports, performs OCR, normalizes data, and generates summaries using LLMs. The frontend provides user interaction and report visualization.

## Architecture & Key Components
- **backend/app/**: Main backend logic, organized by domain:
  - `api/`: FastAPI route handlers (auth, upload, report APIs)
  - `core/`: Core logic (evaluation, unit resolution)
  - `ingest/`: Parsers for ingesting and extracting data
  - `kb/`: Knowledge base loaders and alias expansion
  - `models/`: Pydantic schemas
  - `normalize/`: Value and unit normalization
  - `ocr/`: OCR extraction logic
  - `rag/`: Retrieval-augmented generation (RAG) store
  - `storage/`: Report storage and persistence
  - `summarize/`: LLM-based summarization
- **frontend/**: NiceGUI app, with `pages/` for UI routes and `components/` for shared UI elements
- **test_reports/**: Sample lab reports (PDFs) for testing

## Developer Workflows
- **Run backend**: `python -m app.main` from `backend/`
- **Run frontend**: `python app_nicegui.py` from `frontend/`
- **Run tests**: Execute test files directly (e.g., `python test_llm_mealplan.py`)
- **Dependencies**: Managed via `requirements.txt` in `backend/`

## Project Conventions
- **Modular structure**: Each domain (API, core, ingest, etc.) is a separate subpackage
- **Pydantic models**: All data schemas in `models/schemas.py`
- **JSON for data**: User and report data stored as JSON (`users.json`, `reports.json`)
- **No global state**: Data flows via function arguments or FastAPI dependency injection
- **Testing**: Test scripts are at the root of `backend/` and use real sample PDFs

## Integration & Patterns
- **API**: FastAPI routes in `api/` call into core/ingest/normalize modules
- **OCR**: `ocr/extract.py` handles PDF extraction, used by upload/report APIs
- **LLM**: `summarize/llm.py` provides summary generation, invoked by report APIs
- **Frontend-backend**: Communicate via HTTP API endpoints

## Examples
- To add a new report type: update `ingest/parser.py`, extend schemas in `models/schemas.py`, and update normalization logic
- To add a new API: create a new file in `api/`, register routes in `routes.py`

## See Also
- `README.md` (project intro)
- `backend/requirements.txt` (dependencies)
- `backend/app/api/routes.py` (API registration)
- `backend/app/models/schemas.py` (data models)
- `frontend/pages/` (UI routes)
