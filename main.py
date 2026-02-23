from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import random
from datetime import datetime
from algorithm import calculate_sm2, get_next_review_date

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
# Frontend build output is in ../frontend/dist
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

OBJECTS_FILE = os.path.join(DATA_DIR, "objects.json")
LOCIS_FILE = os.path.join(DATA_DIR, "locis.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

# Ensure Data Dir Exists
os.makedirs(DATA_DIR, exist_ok=True)

# Models
class ObjectItem(BaseModel):
    id: str
    name: str
    image_url: str

class LociItem(BaseModel):
    id: str
    name: str
    image_url: str

class TestResult(BaseModel):
    object_id: str
    is_correct: bool

# API Endpoints
@app.get("/objects", response_model=List[ObjectItem])
def get_objects():
    if not os.path.exists(OBJECTS_FILE):
        return []
    with open(OBJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/locis", response_model=List[LociItem])
def get_locis():
    if not os.path.exists(LOCIS_FILE):
        return []
    with open(LOCIS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/due_objects", response_model=List[ObjectItem])
def get_due_objects():
    # Load Objects
    all_objects = []
    if os.path.exists(OBJECTS_FILE):
        with open(OBJECTS_FILE, "r", encoding="utf-8") as f:
            all_objects = json.load(f)
            
    # Load Stats
    stats = []
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
            
    now = datetime.now()
    due_ids = []
    
    for stat in stats:
        if "next_review" in stat:
            try:
                review_date = datetime.fromisoformat(stat["next_review"])
                if review_date <= now:
                    due_ids.append(stat["object_id"])
            except ValueError:
                pass 
                
    due_objects = [obj for obj in all_objects if obj["id"] in due_ids]
    
    # Fill with new/random if needed
    if len(due_objects) < 5:
        reviewed_ids = set(stat["object_id"] for stat in stats)
        new_objects = [obj for obj in all_objects if obj["id"] not in reviewed_ids]
        random.shuffle(new_objects)
        needed = 5 - len(due_objects)
        due_objects.extend(new_objects[:needed])
        
    if len(due_objects) < 5:
        remaining = [obj for obj in all_objects if obj not in due_objects]
        random.shuffle(remaining)
        needed = 5 - len(due_objects)
        due_objects.extend(remaining[:needed])
        
    return due_objects[:5]

@app.post("/submit_result")
def submit_result(result: TestResult):
    stats = []
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
    
    current_stat = next((item for item in stats if item["object_id"] == result.object_id), None)
    
    if not current_stat:
        current_stat = {
            "object_id": result.object_id,
            "interval": 0,
            "repetitions": 0,
            "e_factor": 2.5,
            "next_review": datetime.now().isoformat()
        }
        stats.append(current_stat)
    
    quality = 5 if result.is_correct else 0
    sm2_result = calculate_sm2(
        quality, 
        current_stat.get("repetitions", 0), 
        current_stat.get("interval", 0), 
        current_stat.get("e_factor", 2.5)
    )
    
    current_stat["repetitions"] = sm2_result["repetitions"]
    current_stat["interval"] = sm2_result["interval"]
    current_stat["e_factor"] = sm2_result["e_factor"]
    current_stat["last_reviewed"] = datetime.now().isoformat()
    current_stat["next_review"] = get_next_review_date(current_stat["last_reviewed"], sm2_result["interval"])
    
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    
    return {"message": "Result saved", "updated_stat": current_stat}

# Serve Frontend Static Files
if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST_DIR, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        file_path = os.path.join(FRONTEND_DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))
else:
    print(f"Warning: Frontend build directory not found at {FRONTEND_DIST_DIR}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
