# VARUNA Backend: Adaptive Forecast Intelligence Platform
Refer to the root [README.md](../README.md) for full architecture, mathematical formulation, API references, demo steps, and deployment documentation.

### Quick Start
```bash
pytest tests/test_all.py -v
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger Documentation: `http://localhost:8000/api/docs`
