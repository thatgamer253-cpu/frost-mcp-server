import os
import stripe
from dotenv import load_dotenv

def setup_webhook():
    load_dotenv()
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        print("Error: STRIPE_SECRET_KEY not found in .env")
        return

    stripe.api_key = api_key
    
    # We use a placeholder URL for local testing or change to your Render URL
    # For local, developers usually use Stripe CLI, but we can register a placeholder to get a secret.
    target_url = "https://frost-mcp-server.onrender.com/webhook"
    
    print(f"Creating Webhook endpoint for {target_url}...")
    
    try:
        webhook = stripe.WebhookEndpoint.create(
            url=target_url,
            enabled_events=[
                "checkout.session.completed",
                "payment_intent.succeeded"
            ],
        )
        secret = webhook.secret
        print(f"Success! Webhook Secret: {secret}")
        
        # Update .env
        env_path = ".env"
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("STRIPE_WEBHOOK_SECRET="):
                new_lines.append(f"STRIPE_WEBHOOK_SECRET={secret}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"\nSTRIPE_WEBHOOK_SECRET={secret}\n")
            
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
            
        print("Updated .env file successfully.")
        
    except Exception as e:
        print(f"Failed to create webhook: {e}")

if __name__ == "__main__":
    setup_webhook()
