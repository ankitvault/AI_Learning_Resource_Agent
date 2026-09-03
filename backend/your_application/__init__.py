import os
import sys

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from main import app as fast_app

app = fast_app
application = fast_app
wsgi = fast_app
