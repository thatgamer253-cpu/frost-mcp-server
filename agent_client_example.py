"""
Example AI Agent Client for Frost Marketplace

This demonstrates how other AI agents can programmatically
discover and purchase services from the Frost marketplace.
"""

import requests
import json

class FrostMarketplaceClient:
    """Client for interacting with Frost AI Agent Marketplace."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_key = None
    
    def discover_services(self):
        """Discover available services in the marketplace."""
        response = requests.get(f"{self.base_url}/services")
        return response.json()
    
    def get_service_details(self, service_id):
        """Get details about a specific service."""
        response = requests.get(f"{self.base_url}/services/{service_id}")
        return response.json()
    
    def purchase_service(self, service_id, agent_id):
        """Purchase a service and receive an API key."""
        response = requests.post(
            f"{self.base_url}/purchase",
            json={
                "service_id": service_id,
                "agent_id": agent_id
            }
        )
        result = response.json()
        
        if result.get("success"):
            self.api_key = result["api_key"]
            print(f"[OK] Purchased: {result['service']}")
            print(f"[OK] API Key: {self.api_key}")
            print(f"[OK] Amount: ${result['amount']}")
        
        return result
    
    def scan_jobs(self, keywords, platforms=["upwork", "linkedin"]):
        """Use the Job Scanner API."""
        if not self.api_key:
            raise Exception("No API key. Purchase the job-scanner-api service first.")
        
        response = requests.post(
            f"{self.base_url}/api/scan",
            headers={"X-API-Key": self.api_key},
            json={
                "keywords": keywords,
                "platforms": platforms
            }
        )
        return response.json()
    
    def generate_cover_letter(self, job_title, job_description, company):
        """Use the Cover Letter Generator API."""
        if not self.api_key:
            raise Exception("No API key. Purchase the cover-letter-generator service first.")
        
        response = requests.post(
            f"{self.base_url}/api/generate-letter",
            headers={"X-API-Key": self.api_key},
            json={
                "job_title": job_title,
                "job_description": job_description,
                "company": company
            }
        )
        return response.json()

# Demo usage
if __name__ == "__main__":
    print("=== Frost Marketplace Demo ===\n")
    
    # Initialize client
    client = FrostMarketplaceClient()
    
    # 1. Discover services
    print("1. Discovering available services...")
    services = client.discover_services()
    print(f"Found {len(services['services'])} services:\n")
    for service in services['services']:
        print(f"  - {service['name']}: ${service['price']} ({service['billing']})")
    
    print("\n" + "="*50 + "\n")
    
    # 2. Purchase Job Scanner API
    print("2. Purchasing Job Scanner API...")
    purchase_result = client.purchase_service(
        service_id="job-scanner-api",
        agent_id="demo-agent-001"
    )
    
    print("\n" + "="*50 + "\n")
    
    # 3. Use the service
    print("3. Using Job Scanner API...")
    scan_result = client.scan_jobs(
        keywords=["Python Developer", "AI Engineer"],
        platforms=["upwork"]
    )
    
    print(f"[OK] Found {scan_result['jobs_found']} jobs")
    if scan_result['jobs']:
        print(f"\nSample job:")
        job = scan_result['jobs'][0]
        print(f"  Title: {job['title']}")
        print(f"  Platform: {job['platform']}")
        print(f"  URL: {job['url']}")
    
    print("\n=== Demo Complete ===")
