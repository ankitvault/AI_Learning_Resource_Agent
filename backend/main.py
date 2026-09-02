import os
import sys

# Ensure backend directory is in sys.path regardless of execution root
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import generate_study_pack
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Study Resource Agent API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StudyRequest(BaseModel):
    board: str
    class_level: str
    subject: str
    topic: str

@app.post("/api/generate")
async def generate_endpoint(request: StudyRequest):
    logger.info(f"Received request for generating study pack: {request.dict()}")
    try:
        result = await generate_study_pack(
            board=request.board,
            class_level=request.class_level,
            subject=request.subject,
            topic=request.topic
        )
        return result
    except Exception as e:
        logger.error(f"Error generating study pack: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "AI Study Resource Agent API is running."}
