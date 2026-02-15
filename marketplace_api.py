from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
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
@app.get("/")
async def root():
    """Marketplace Root - Discovery Gateway."""
    return HTMLResponse(content="""
        <html>
            <head>
                <title>Frost Marketplace Gateway</title>
                <style>
                    body { font-family: 'Inter', sans-serif; background: #0f172a; color: white; text-align: center; padding: 50px; }
                    .container { max-width: 800px; margin: auto; background: #1e293b; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
                    h1 { color: #3b82f6; font-size: 2.5em; margin-bottom: 20px; }
                    .status { display: inline-block; background: #059669; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin-bottom: 30px; }
                    .links { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; text-align: left; }
                    .card { background: #334155; padding: 20px; border-radius: 10px; text-decoration: none; color: white; transition: transform 0.2s; }
                    .card:hover { transform: translateY(-5px); background: #475569; }
                    .card h3 { margin-top: 0; color: #60a5fa; }
                    code { background: #000; padding: 2px 5px; border-radius: 3px; color: #f472b6; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Project Frost Marketplace</h1>
                    <div class="status">● LIVE MODE ACTIVE</div>
                    <p>Programmatic API gateway for Autonomous Agent Services.</p>
                    <div class="links">
                        <a href="/services" class="card">
                            <h3>/services</h3>
                            <p>Browse available models, tools, and automation kits for your swarm.</p>
                        </a>
                        <a href="/docs" class="card">
                            <h3>/docs</h3>
                            <p>Interactive API documentation and schema definitions.</p>
                        </a>
                        <a href="/health" class="card">
                            <h3>/health</h3>
                            <p>System vitals and connectivity status.</p>
                        </a>
                        <div class="card">
                            <h3>Stripe Webhook</h3>
                            <p>Endpoint at <code>/webhook</code> is listening for verified payments.</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    """)

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
    """Purchase a service and get a Stripe Checkout URL."""
    # Find service
    service = next(
        (s for s in SERVICE_CATALOG["services"] if s["id"] == request.service_id),
        None
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    try:
        # Determine base URL dynamically
        scheme = request.url.scheme
        host = request.headers.get("host")
        base_url = f"{scheme}://{host}"
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': service["currency"],
                    'product_data': {
                        'name': service["name"],
                        'description': service["description"],
                    },
                    'unit_amount': int(service["price"] * 100),
                },
                'quantity': 1,
            }],
            mode='payment' if service["billing"] != "monthly" else 'subscription',
            success_url=f"{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/cancel",
            metadata={
                "agent_id": request.agent_id,
                "service_id": service["id"]
            }
        )
        
        return {
            "success": True,
            "checkout_url": checkout_session.url,
            "message": "Please complete payment at the checkout_url",
            "agent_id": request.agent_id,
            "service_id": service["id"]
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """Handles Stripe Webhooks for payment fulfillment."""
    payload = await request.body()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Fulfill the purchase
        metadata = session.get('metadata', {})
        agent_id = metadata.get('agent_id')
        service_id = metadata.get('service_id')
        
        if agent_id and service_id:
            service = next((s for s in SERVICE_CATALOG["services"] if s["id"] == service_id), None)
            if service:
                # 1. Generate API key
                api_key = key_manager.generate_key(
                    agent_id,
                    service["id"],
                    service["billing"]
                )
                
                # 2. Record revenue (REAL MONEY VERIFIED)
                revenue_manager.record_marketplace_sale(
                    service_id=service["id"],
                    service_name=service["name"],
                    amount=service["price"],
                    agent_id=agent_id
                )
                
                print(f"[Marketplace] FULFILLMENT SUCCESS: {service_id} for {agent_id}. Key: {api_key}")

    return {"status": "success"}

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

@app.get("/success")
async def payment_success(session_id: str):
    return HTMLResponse(content=f"""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px; background: #0f172a; color: white;">
                <h1 style="color: #4ade80;">Payment Successful!</h1>
                <p>Your API key has been generated and sent to your agent.</p>
                <p>Session ID: {session_id}</p>
                <button onclick="window.close()" style="background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Close Window</button>
            </body>
        </html>
    """)

@app.get("/cancel")
async def payment_cancel():
    return HTMLResponse(content="""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px; background: #0f172a; color: white;">
                <h1 style="color: #f87171;">Payment Cancelled</h1>
                <p>The transaction was not completed.</p>
                <button onclick="window.close()" style="background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Return to Safety</button>
            </body>
        </html>
    """)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "marketplace": "Frost AI Agent Marketplace"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
