#!/usr/bin/env python3
"""Quick test of API endpoints."""

import requests
import json

# Test Google Gemini
print("Testing Google Gemini...")
google_key = "GOOGLE_API_KEY_PLACEHOLDER"
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-exp:generateContent?key={google_key}"
data = {
    "contents": [{
        "parts": [{"text": "Say 'Hello' in 5 words"}]
    }],
    "generationConfig": {"maxOutputTokens": 50}
}

try:
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("Response:", json.dumps(result, indent=2)[:500])
    else:
        print("Error:", response.text[:500])
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*60)
print("Testing Cerebras...")
cerebras_key = "CEREBRAS_API_KEY_PLACEHOLDER"
url = "https://api.cerebras.ai/v1/chat/completions"
headers = {"Authorization": f"Bearer {cerebras_key}", "Content-Type": "application/json"}
data = {"model": "llama3.1-8b", "messages": [{"role": "user", "content": "Say 'Hello' in 5 words"}], "max_tokens": 50}

try:
    response = requests.post(url, json=data, headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("Response:", json.dumps(result, indent=2)[:500])
    else:
        print("Error:", response.text[:500])
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*60)
print("Testing Groq...")
groq_key = "GROQ_API_KEY_PLACEHOLDER"
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
data = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "Say 'Hello' in 5 words"}], "max_tokens": 50}

try:
    response = requests.post(url, json=data, headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print("Response:", json.dumps(result, indent=2)[:500])
    else:
        print("Error:", response.text[:500])
except Exception as e:
    print(f"Exception: {e}")
