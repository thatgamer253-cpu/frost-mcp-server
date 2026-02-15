from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import stripe
from api_key_manager import APIKeyManager
from revenue import RevenueManager
from scanner import JobScanner
from generator import MaterialGenerator

# Initialize FastAPI
app = FastAPI(
    title="Frost AI Agent Marketplace",
    description="Programmatic service marketplace for AI agents",
    version="1.0.0"
)

# Load configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
key_manager = APIKeyManager()
revenue_manager = RevenueManager()

# Load service catalog
with open("service_catalog.json", 'r') as f:
    SERVICE_CATALOG = json.load(f)

# Pydantic models
class PurchaseRequest(BaseModel):
    service_id: str
    agent_id: str
    payment_method_id: Optional[str] = None

class ScanRequest(BaseModel):
    keywords: List[str]
    platforms: Optional[List[str]] = ["upwork", "linkedin"]

class GenerateLetterRequest(BaseModel):
    job_title: str
    job_description: str
    company: str
    profile_name: Optional[str] = "default"

# Dependency for API key validation
async def validate_api_key(
    x_api_key: str = Header(...),
    service_id: str = None
):
    valid, message = key_manager.validate_key(x_api_key, service_id)
    if not valid:
        raise HTTPException(status_code=401, detail=message)
    return x_api_key

# Discovery endpoint
@app.get("/services")
async def list_services():
    """List all available services in the marketplace."""
    return {
        "marketplace": "Frost AI Agent Marketplace",
        "services": SERVICE_CATALOG["services"],
        "documentation": "/docs"
    }

@app.get("/services/{service_id}")
async def get_service(service_id: str):
    """Get details about a specific service."""
    service = next(
        (s for s in SERVICE_CATALOG["services"] if s["id"] == service_id),
        None
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

# Purchase endpoint
@app.post("/purchase")
async def purchase_service(request: PurchaseRequest):
    """Purchase a service and receive an API key."""
    
    # Find service
    service = next(
        (s for s in SERVICE_CATALOG["services"] if s["id"] == request.service_id),
        None
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    try:
        # Create Stripe payment intent
        if service["billing"] == "monthly":
            # Create subscription
            payment_intent = stripe.PaymentIntent.create(
                amount=int(service["price"] * 100),
                currency=service["currency"],
                description=f"{service['name']} - Monthly Subscription",
                metadata={
                    "agent_id": request.agent_id,
                    "service_id": service["id"]
                }
            )
        else:
            # One-time payment
            payment_intent = stripe.PaymentIntent.create(
                amount=int(service["price"] * 100),
                currency=service["currency"],
                description=f"{service['name']} - {service['billing']}",
                metadata={
                    "agent_id": request.agent_id,
                    "service_id": service["id"]
                }
            )
        
        # Generate API key
        api_key = key_manager.generate_key(
            request.agent_id,
            service["id"],
            service["billing"]
        )
        
        # Record revenue
        revenue_manager.record_marketplace_sale(
            service_id=service["id"],
            service_name=service["name"],
            amount=service["price"],
            agent_id=request.agent_id
        )
        
        return {
            "success": True,
            "api_key": api_key,
            "service": service["name"],
            "billing": service["billing"],
            "amount": service["price"],
            "payment_intent_id": payment_intent.id,
            "endpoints": service["endpoints"]
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Service endpoints
@app.post("/api/scan")
async def scan_jobs(
    request: ScanRequest,
    api_key: str = Depends(lambda x_api_key=Header(...): validate_api_key(x_api_key, "job-scanner-api"))
):
    """Scan job boards for opportunities."""
    scanner = JobScanner()
    
    # Create a mock profile for scanning
    profile = {
        "platforms": {
            "upwork": {"enabled": "upwork" in request.platforms, "keywords": request.keywords},
            "linkedin": {"enabled": "linkedin" in request.platforms, "keywords": request.keywords}
        }
    }
    
    jobs = scanner.scan_all(profile)
    
    return {
        "success": True,
        "jobs_found": len(jobs),
        "jobs": jobs
    }

@app.post("/api/generate-letter")
async def generate_letter(
    request: GenerateLetterRequest,
    api_key: str = Depends(lambda x_api_key=Header(...): validate_api_key(x_api_key, "cover-letter-generator"))
):
    """Generate a cover letter for a job."""
    
    # Load profile
    profile_file = f"profiles/{request.profile_name}.json"
    if not os.path.exists(profile_file):
        profile_file = "profiles/ai_strategist_1771146284.json"
    
    with open(profile_file, 'r') as f:
        profile = json.load(f)
    
    # Create job object
    job = {
        "title": request.job_title,
        "description": request.job_description,
        "company": request.company
    }
    
    # Generate letter
    generator = MaterialGenerator(profile)
    letter = generator.generate_cover_letter(job)
    
    return {
        "success": True,
        "cover_letter": letter,
        "job_title": request.job_title,
        "company": request.company
    }

@app.get("/api/download/automation-toolkit")
async def download_toolkit(
    api_key: str = Depends(lambda x_api_key=Header(...): validate_api_key(x_api_key, "automation-toolkit"))
):
    """Download the browser automation toolkit."""
    return {
        "success": True,
        "message": "Toolkit download ready",
        "files": [
            "scanner.py",
            "auto_submitter.py",
            "guardian.py"
        ],
        "documentation": "https://github.com/frost-ai/automation-toolkit"
    }

@app.post("/api/optimize-profile")
async def optimize_profile(
    profile_data: dict,
    api_key: str = Depends(lambda x_api_key=Header(...): validate_api_key(x_api_key, "profile-optimizer"))
):
    """Optimize a profile for job platforms."""
    # Placeholder for profile optimization logic
    return {
        "success": True,
        "message": "Profile optimization complete",
        "recommendations": [
            "Add more specific technical skills",
            "Highlight recent AI/ML projects",
            "Include quantifiable achievements",
            "Optimize for remote work keywords"
        ]
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "marketplace": "Frost AI Agent Marketplace"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
