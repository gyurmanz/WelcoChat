# Entry point for cPanel's "Setup Python App" (Phusion Passenger).
# Passenger loads this file and calls the WSGI-callable named "application"
# (set as the app's "entry point" in cPanel). FastAPI is ASGI, not WSGI, so
# a2wsgi wraps it — this keeps the app portable across Passenger versions
# without depending on Passenger's native (and version-dependent) ASGI support.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2wsgi import ASGIMiddleware
from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
