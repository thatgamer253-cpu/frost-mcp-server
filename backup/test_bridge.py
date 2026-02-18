import requests
import os

def test_bridge():
    print("Testing PixelBridge (tmpfiles.org)...")
    
    # Create dummy image
    img_path = "dummy_bridge.png"
    with open(img_path, "wb") as f:
        f.write(os.urandom(1024)) # Random bytes
        
    url = "https://tmpfiles.org/api/v1/upload"
    
    try:
        with open(img_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(url, files=files)
            
        if resp.status_code == 200:
            data = resp.json()
            # tmpfiles returns a URL like https://tmpfiles.org/12345/file.png
            # BUT the direct download link is slightly different usually.
            # Let's check the response structure.
            print(f"Response: {data}")
            
            raw_url = data["data"]["url"]
            print(f"Raw URL: {raw_url}")
            
            # tmpfiles.org download link requires replacing "tmpfiles.org/" with "tmpfiles.org/dl/"
            dl_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            print(f"Direct Link: {dl_url}")
            
            # Verify accessibility
            r = requests.head(dl_url)
            if r.status_code == 200:
                print("Bridge Verified: Direct link is accessible.")
            else:
                print(f"Bridge Error: Direct link returned {r.status_code}")
        else:
             print(f"Bridge Upload Failed: {resp.status_code}")

    except Exception as e:
        print(f"Exception: {e}")
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

if __name__ == "__main__":
    test_bridge()
