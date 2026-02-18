import requests

key = "40ae31e5e44616391008a0fcebaf4e77"
url = "https://api.kie.ai/api/v1/jobs/createTask"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# Exact payload from docs for Master Text-to-Video
payload = {
    "model": "kling/v2-1-master-text-to-video",
    "callBackUrl": "https://example.com/callback",
    "input": {
        "prompt": "A cinematic animation of kids flying kites on a sunny hill with clear blue skies, birds soaring, warm sunlight, high quality 4k.",
        "duration": "5",
        "aspect_ratio": "16:9",
        "negative_prompt": "blur, distort, low quality",
        "cfg_scale": 0.5
    }
}

print("Testing Kling v2.1 Master Text-to-Video...")
r = requests.post(url, headers=headers, json=payload, timeout=20)
print(f"Result: {r.status_code} - {r.text}")
