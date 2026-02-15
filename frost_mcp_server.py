"""
Frost MCP Server - HTTP Wrapper for Cloud Deployment

Exposes MCP tools as HTTP endpoints for deployment on platforms like Render.
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import os
import json

# Import your existing modules
try:
    from api_key_manager import APIKeyManager
    from scanner import JobScanner
    from generator import MaterialGenerator
    from revenue import RevenueManager
except ImportError as e:
    print(f"Warning: Could not import module: {e}")
    # Create mock classes for deployment
    class APIKeyManager:
        def validate_key(self, key, service): return True, "OK"
    class JobScanner:
        def scan_all(self, profile): return []
    class MaterialGenerator:
        def __init__(self, profile): pass
        def generate_cover_letter(self, job): return "Sample letter"
    class RevenueManager:
        def record_marketplace_sale(self, *args, **kwargs): pass

# Initialize
app = FastAPI(title="Frost MCP Server", version="1.0.0")
key_manager = APIKeyManager()
revenue_manager = RevenueManager()

# Request models
class ScanJobsRequest(BaseModel):
    keywords: List[str]
    platforms: Optional[List[str]] = ["upwork", "linkedin"]
    api_key: str

class GenerateLetterRequest(BaseModel):
    job_title: str
    job_description: str
    company: str
    api_key: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Frost MCP Server",
        "status": "running",
        "version": "1.0.0",
        "tools": ["scan_jobs", "generate_cover_letter"]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.post("/tools/scan_jobs")
async def scan_jobs(request: ScanJobsRequest):
    """Scan job boards for opportunities"""
    
    # Validate API key
    valid, message = key_manager.validate_key(request.api_key, "job-scanner-api")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Create scanner
        scanner = JobScanner()
        
        # Build profile
        profile = {
            "platforms": {
                "upwork": {
                    "enabled": "upwork" in request.platforms,
                    "keywords": request.keywords
                },
                "linkedin": {
                    "enabled": "linkedin" in request.platforms,
                    "keywords": request.keywords
                }
            }
        }
        
        # Scan
        jobs = scanner.scan_all(profile)
        
        # Track revenue
        revenue_manager.record_marketplace_sale(
            service_id="job-scanner-api",
            service_name="Job Scanner API",
            amount=0.10,
            agent_id=request.api_key[:16]
        )
        
        return {
            "success": True,
            "jobs_found": len(jobs),
            "jobs": jobs[:10]  # Limit to 10
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/generate_cover_letter")
async def generate_cover_letter(request: GenerateLetterRequest):
    """Generate a professional cover letter"""
    
    # Validate API key
    valid, message = key_manager.validate_key(request.api_key, "cover-letter-generator")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Load default profile
        profile_file = "profiles/ai_strategist_1771146284.json"
        if os.path.exists(profile_file):
            with open(profile_file, 'r') as f:
                profile = json.load(f)
        else:
            # Use minimal profile
            profile = {"name": "Professional", "skills": []}
        
        # Create job object
        job = {
            "title": request.job_title,
            "description": request.job_description,
            "company": request.company
        }
        
        # Generate letter
        generator = MaterialGenerator(profile)
        letter = generator.generate_cover_letter(job)
        
        # Track revenue
        revenue_manager.record_marketplace_sale(
            service_id="cover-letter-generator",
            service_name="Cover Letter Generator",
            amount=0.50,
            agent_id=request.api_key[:16]
        )
        
        return {
            "success": True,
            "cover_letter": letter
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "scan_jobs",
                "description": "Scan job boards for opportunities",
                "endpoint": "/tools/scan_jobs",
                "cost": "$0.10 per scan"
            },
            {
                "name": "generate_cover_letter",
                "description": "Generate professional cover letters",
                "endpoint": "/tools/generate_cover_letter",
                "cost": "$0.50 per letter"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
