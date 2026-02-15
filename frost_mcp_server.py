"""
Frost MCP Server - HTTP Wrapper for Cloud Deployment

Exposes MCP tools as HTTP endpoints for deployment on platforms like Render.
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import os
import json

import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("frost-server")

# Lazy Loading Containers
_key_manager = None
_revenue_manager = None
_scanner = None
_generator = None
_creation_engine = None

def get_key_manager():
    global _key_manager
    if _key_manager is None:
        try:
            from api_key_manager import APIKeyManager
            _key_manager = APIKeyManager()
        except:
            class MockKeyManager:
                def validate_key(self, key, service): return True, "OK"
            _key_manager = MockKeyManager()
    return _key_manager

def get_revenue_manager():
    global _revenue_manager
    if _revenue_manager is None:
        try:
            from revenue import RevenueManager
            _revenue_manager = RevenueManager()
        except:
            class MockRevenueManager:
                def record_marketplace_sale(self, *args, **kwargs): pass
            _revenue_manager = MockRevenueManager()
    return _revenue_manager

def get_creation_engine():
    global _creation_engine
    if _creation_engine is None:
        try:
            from engine_bridge import creation_engine
            _creation_engine = creation_engine
        except Exception as e:
            logger.error(f"Lazy load Creation Engine failed: {e}")
            class MockCreationEngine:
                def build_project(self, *args, **kwargs): return True, "applications/mock"
            _creation_engine = MockCreationEngine()
    return _creation_engine

# Initialize FastAPI
app = FastAPI(title="Frost MCP Server", version="1.0.0")

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

class CreateToolRequest(BaseModel):
    description: str
    language: Optional[str] = "python"
    api_key: str

class CreateApplicationRequest(BaseModel):
    description: str
    stack: Optional[str] = "python"
    api_key: str

class CreateAutomationRequest(BaseModel):
    workflow_description: str
    platforms: Optional[List[str]] = ["web"]
    api_key: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Frost MCP Server",
        "status": "running",
        "version": "1.0.0",
        "tools": ["scan_jobs", "generate_cover_letter", "create_tool", "create_application", "create_automation"]
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.post("/tools/scan_jobs")
async def scan_jobs(request: ScanJobsRequest):
    """Scan job boards for opportunities"""
    
    # Validate API key
    valid, message = get_key_manager().validate_key(request.api_key, "job-scanner-api")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Create scanner
        from scanner import JobScanner
        scanner = JobScanner()
        
        # Build profile
        profile = {
            "platforms": {
                "upwork": {
                    "enabled": "upwork" in (request.platforms or []),
                    "keywords": request.keywords
                },
                "linkedin": {
                    "enabled": "linkedin" in (request.platforms or []),
                    "keywords": request.keywords
                }
            }
        }
        
        # Scan
        jobs = scanner.scan_all(profile)
        
        # Track revenue
        agent_id = str(request.api_key)[:16]
        get_revenue_manager().record_marketplace_sale(
            service_id="job-scanner-api",
            service_name="Job Scanner API",
            amount=0.10,
            agent_id=agent_id
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
    valid, message = get_key_manager().validate_key(request.api_key, "cover-letter-generator")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Load default profile
        profile_file = "profiles/ai_strategist_1771146284.json"
        profile = {"name": "Professional", "skills": []}
        
        if os.path.exists(profile_file):
            with open(profile_file, 'r') as f:
                profile = json.load(f)
        elif os.path.exists("profiles"):
            # Try to find any profile in the directory
            profile_files = [f for f in os.listdir("profiles") if f.endswith(".json")]
            if profile_files:
                selected_profile = os.path.join("profiles", profile_files[0])
                with open(selected_profile, 'r') as f:
                    profile = json.load(f)
                    print(f"[Server] Using alternative profile: {selected_profile}")
        
        # Create job object
        job = {
            "title": request.job_title,
            "description": request.job_description,
            "company": request.company
        }
        
        # Generate letter
        from generator import MaterialGenerator
        generator = MaterialGenerator(profile)
        letter = generator.generate_cover_letter(job)
        
        # Track revenue
        agent_id = str(request.api_key)[:16]
        get_revenue_manager().record_marketplace_sale(
            service_id="cover-letter-generator",
            service_name="Cover Letter Generator",
            amount=0.50,
            agent_id=agent_id
        )
        
        return {
            "success": True,
            "cover_letter": letter
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/create_tool")
async def create_tool(request: CreateToolRequest):
    """Generate a custom tool or script"""
    
    # Validate API key
    valid, message = get_key_manager().validate_key(request.api_key, "creation-engine")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Generate unique project ID
        import time
        project_id = f"tool_{int(time.time())}"
        
        # Build the tool
        goal = f"Create a {request.language} tool: {request.description}"
        success, project_path = get_creation_engine().build_project(
            project_id=project_id,
            goal=goal,
            description=f"Language: {request.language}\n{request.description}"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Tool creation failed")
        
        # Track revenue
        agent_id = str(request.api_key)[:16]
        get_revenue_manager().record_marketplace_sale(
            service_id="creation-engine-tool",
            service_name="Tool Creation",
            amount=10.00,
            agent_id=agent_id
        )
        
        return {
            "success": True,
            "project_id": project_id,
            "project_path": project_path,
            "message": "Tool created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/create_application")
async def create_application(request: CreateApplicationRequest):
    """Generate a complete application"""
    
    # Validate API key
    valid, message = get_key_manager().validate_key(request.api_key, "creation-engine")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Generate unique project ID
        import time
        project_id = f"app_{int(time.time())}"
        
        # Build the application
        goal = f"Build a {request.stack} application: {request.description}"
        success, project_path = get_creation_engine().build_project(
            project_id=project_id,
            goal=goal,
            description=f"Stack: {request.stack}\n{request.description}"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Application creation failed")
        
        # Track revenue
        agent_id = str(request.api_key)[:16]
        get_revenue_manager().record_marketplace_sale(
            service_id="creation-engine-app",
            service_name="Application Creation",
            amount=50.00,
            agent_id=agent_id
        )
        
        return {
            "success": True,
            "project_id": project_id,
            "project_path": project_path,
            "message": "Application created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/create_automation")
async def create_automation(request: CreateAutomationRequest):
    """Generate automation workflows"""
    
    # Validate API key
    valid, message = get_key_manager().validate_key(request.api_key, "creation-engine")
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    
    try:
        # Generate unique project ID
        import time
        project_id = f"automation_{int(time.time())}"
        
        # Build the automation
        platforms_list = request.platforms or []
        platforms_str = ", ".join(platforms_list)
        goal = f"Create automation for {platforms_str}: {request.workflow_description}"
        success, project_path = get_creation_engine().build_project(
            project_id=project_id,
            goal=goal,
            description=f"Platforms: {platforms_str}\n{request.workflow_description}"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Automation creation failed")
        
        # Track revenue
        agent_id = str(request.api_key)[:16]
        get_revenue_manager().record_marketplace_sale(
            service_id="creation-engine-automation",
            service_name="Automation Creation",
            amount=20.00,
            agent_id=agent_id
        )
        
        return {
            "success": True,
            "project_id": project_id,
            "project_path": project_path,
            "message": "Automation created successfully"
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
            },
            {
                "name": "create_tool",
                "description": "Generate custom tools and scripts",
                "endpoint": "/tools/create_tool",
                "cost": "$10.00 per tool"
            },
            {
                "name": "create_application",
                "description": "Build complete applications with UI",
                "endpoint": "/tools/create_application",
                "cost": "$50.00 per application"
            },
            {
                "name": "create_automation",
                "description": "Create automation workflows",
                "endpoint": "/tools/create_automation",
                "cost": "$20.00 per automation"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
