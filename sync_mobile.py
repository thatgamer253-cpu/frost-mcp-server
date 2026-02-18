
import os
import agent_ipc

def sync():
    ip = "192.168.0.207"
    port = "3000"
    url = f"http://{ip}:{port}"
    
    msg = f"📱 SOVEREIGN MOBILE SYNC: Your portal is ready at {url}. Open this on your phone's browser to connect to the Council."
    
    print("\n" + "="*50)
    print("🚀 MOBILE DEPLOYMENT ACTIVE")
    print(f"🔗 Local URL: {url}")
    print("="*50)
    print("\nSTEPS TO INSTALL:")
    print("1. Ensure your phone is on the same Wi-Fi.")
    print(f"2. Navigate to {url} in your mobile browser.")
    print("3. Tap 'Add to Home Screen' for the native experience.")
    print("\nSTANDING BY FOR CONNECTION...")
    
    # Broadcast to Council
    agent_ipc.broadcast("STATUS", "nirvash", msg)

if __name__ == "__main__":
    sync()
