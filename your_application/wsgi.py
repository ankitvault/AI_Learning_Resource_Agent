import os
import sys

# Ensure root directory and backend directory are in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from a2wsgi import ASGIMiddleware
from backend.main import app as fast_app

# Expose WSGI application so Render's default 'gunicorn your_application.wsgi' command works out of the box
application = ASGIMiddleware(fast_app)
app = application
