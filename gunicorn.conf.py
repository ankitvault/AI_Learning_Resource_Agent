import os

# Use uvicorn worker for async FastAPI support in Gunicorn
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
