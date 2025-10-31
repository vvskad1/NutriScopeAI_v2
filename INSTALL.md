# Installation Guide for NutriScope AI v3

## Quick Start (Minimum Requirements)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Frontend Setup
```bash
cd frontend
pip install -r requirements.txt
```

### 3. Start Application
```bash
# Terminal 1: Backend
cd backend
.venv\Scripts\Activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
python app_nicegui.py
```

## Full Installation (Including LLM Training)

### For Local Model Training/Inference:
```bash
cd backend
pip install -r requirements-training.txt
```

## Installation Options

### Option 1: Basic Setup (API Mode Only)
```bash
pip install -r requirements.txt
```
- Use `USE_LOCAL_MODEL = False` in config
- Requires API keys (OpenAI, etc.)

### Option 2: Full Setup (Local + API Mode)
```bash
pip install -r requirements.txt
pip install -r requirements-training.txt
```
- Use `USE_LOCAL_MODEL = True` for privacy mode
- Use `USE_LOCAL_MODEL = False` for API mode

## System Requirements

### Minimum (API Mode):
- Python 3.8+
- 4GB RAM
- 1GB storage

### Recommended (Local Model):
- Python 3.10+
- 16GB+ RAM
- CUDA-compatible GPU (8GB+ VRAM)
- 10GB+ storage

## Troubleshooting

### Virtual Environment Issues:
If you get path errors, recreate the virtual environment:
```bash
Remove-Item -Recurse -Force .venv  # Windows
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
```

### GPU Issues:
For CUDA support:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Memory Issues:
Reduce batch size in config files or use API mode instead of local model.