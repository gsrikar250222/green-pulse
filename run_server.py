"""
GreenPulse Platform Launcher
Starts the unified full-stack server hosting:
- Farmer Website (frontend/index.html) at http://localhost:8000/
- Admin Portal (frontend/admin.html)   at http://localhost:8000/admin
- Interactive API Docs (FastAPI)     at http://localhost:8000/api/docs
- REST API v1                        at http://localhost:8000/api/v1/
"""
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(base_dir, "backend")
sys.path.insert(0, backend_dir)

import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print(" 🌱 GREENPULSE – PRODUCTION-READY AGRICULTURE PLATFORM")
    print("=" * 65)
    print("  🌐 Farmer Portal:    http://localhost:8000/")
    print("  🔐 Admin Portal:     http://localhost:8000/admin")
    print("  📚 API Docs:         http://localhost:8000/api/docs")
    print("  🔑 Admin Demo Login: admin@greenpulse.in / Admin@123456")
    print("=" * 65 + "\n")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, app_dir=backend_dir)

