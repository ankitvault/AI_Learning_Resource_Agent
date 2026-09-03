import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from backend.main import app as fast_app
except ImportError:
    from main import app as fast_app

from a2wsgi import ASGIMiddleware

application = ASGIMiddleware(fast_app)
wsgi = application
app = fast_app
