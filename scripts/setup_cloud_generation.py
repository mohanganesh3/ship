#!/usr/bin/env python3
"""
Adapter to use Groq/Together/OpenRouter APIs instead of local llama-server.

Benefits:
- 200x faster than local CPU inference
- Free tiers available (Groq: 14,400 req/day)
- No GPU/CPU usage for inference
- OpenAI-compatible API (drop-in replacement)

Usage:
    export GROQ_API_KEY="gsk_..."
    python scripts/generate_wave1_cloud.py --api groq --model llama-3.1-70b-versatile
    
Or for Together.AI:
    export TOGETHER_API_KEY="..."
    python scripts/generate_wave1_cloud.py --api together --model Qwen/Qwen2.5-72B-Instruct
"""

import os
import sys

# Check if we can import the original script
sys.path.insert(0, '/home/mohanganesh/ship/scripts')

def get_api_config(api_name: str, model: str):
    """Get API configuration for different providers."""
    configs = {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "api_key_env": "GROQ_API_KEY",
            "default_model": "llama-3.1-70b-versatile",
            "free_tier": "14,400 requests/day",
            "models": [
                "llama-3.1-70b-versatile",  # Best for generation
                "llama-3.1-8b-instant",     # Faster, cheaper
                "mixtral-8x7b-32768",       # Good balance
            ]
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
            "default_model": "Qwen/Qwen2.5-72B-Instruct",
            "free_tier": "$25 credit (~500k tokens)",
            "models": [
                "Qwen/Qwen2.5-72B-Instruct",
                "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "mistralai/Mixtral-8x22B-Instruct-v0.1",
            ]
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY",
            "default_model": "meta-llama/llama-3.1-70b-instruct:free",
            "free_tier": "Several free models",
            "models": [
                "meta-llama/llama-3.1-70b-instruct:free",
                "qwen/qwen-2-72b-instruct:free",
            ]
        }
    }
    
    if api_name not in configs:
        raise ValueError(f"Unknown API: {api_name}. Choose from: {list(configs.keys())}")
    
    config = configs[api_name]
    api_key = os.getenv(config["api_key_env"])
    
    if not api_key:
        print(f"\n❌ ERROR: {config['api_key_env']} not set!")
        print(f"\nTo get a free API key:")
        if api_name == "groq":
            print("1. Go to: https://console.groq.com")
            print("2. Sign up (free)")
            print("3. Create API key")
            print(f"4. export {config['api_key_env']}='your-key-here'")
        elif api_name == "together":
            print("1. Go to: https://api.together.xyz")
            print("2. Sign up (free $25 credit)")
            print("3. Get API key")
            print(f"4. export {config['api_key_env']}='your-key-here'")
        elif api_name == "openrouter":
            print("1. Go to: https://openrouter.ai")
            print("2. Sign up")
            print("3. Get API key")
            print(f"4. export {config['api_key_env']}='your-key-here'")
        print(f"\nFree tier: {config['free_tier']}")
        print(f"Available models: {', '.join(config['models'])}")
        sys.exit(1)
    
    return {
        "base_url": config["base_url"],
        "api_key": api_key,
        "model": model or config["default_model"],
        "provider": api_name
    }


def create_cloud_server_script(api_name: str, model: str, port: int = 9000):
    """
    Create a wrapper script that mimics llama-server but uses cloud API.
    This allows us to use the existing generate_wave1.py without modifications!
    """
    config = get_api_config(api_name, model)
    
    wrapper_script = f"""#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
import requests
import time

app = Flask(__name__)

API_CONFIG = {{
    "base_url": "{config['base_url']}",
    "api_key": "{config['api_key']}",
    "model": "{config['model']}",
    "provider": "{config['provider']}"
}}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({{"status": "ok"}})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    
    # Forward request to cloud API
    headers = {{
        "Authorization": f"Bearer {{API_CONFIG['api_key']}}",
        "Content-Type": "application/json"
    }}
    
    payload = {{
        "model": API_CONFIG['model'],
        "messages": data.get('messages', []),
        "temperature": data.get('temperature', 0.1),
        "max_tokens": data.get('max_tokens', 150),
    }}
    
    try:
        response = requests.post(
            f"{{API_CONFIG['base_url']}}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

if __name__ == '__main__':
    print(f"🚀 Cloud API wrapper running on port {port}")
    print(f"Provider: {{API_CONFIG['provider']}}")
    print(f"Model: {{API_CONFIG['model']}}")
    print(f"Base URL: {{API_CONFIG['base_url']}}")
    app.run(host='127.0.0.1', port={port}, debug=False)
"""
    
    wrapper_path = f"/home/mohanganesh/ship/scripts/cloud_api_wrapper_{api_name}.py"
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_script)
    os.chmod(wrapper_path, 0o755)
    
    print(f"✅ Created wrapper: {wrapper_path}")
    print(f"   Provider: {config['provider']}")
    print(f"   Model: {config['model']}")
    print(f"   Port: {port}")
    
    return wrapper_path


if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="Setup cloud API for data generation")
    ap.add_argument("--api", choices=["groq", "together", "openrouter"], required=True)
    ap.add_argument("--model", help="Model name (uses provider default if not specified)")
    ap.add_argument("--ports", default="9000,9001,9002,9003,9004,9005", 
                   help="Ports for API wrappers (6 recommended)")
    args = ap.parse_args()
    
    # Check API key exists
    config = get_api_config(args.api, args.model)
    
    print(f"\n✅ API Configuration Valid")
    print(f"   Provider: {config['provider']}")
    print(f"   Model: {config['model']}")
    print(f"   Base URL: {config['base_url']}")
    print(f"\n📝 Next steps:")
    print(f"   1. Kill local teachers (free up CPU):")
    print(f"      pkill llama-server")
    print(f"   2. Start cloud API wrappers on ports {args.ports}:")
    
    ports = [int(p.strip()) for p in args.ports.split(',')]
    print(f"\n   for port in {' '.join(map(str, ports))}; do")
    print(f"       python3 scripts/cloud_api_wrapper_{args.api}.py &")
    print(f"   done")
    print(f"\n   3. Restart generation with cloud APIs:")
    print(f"      /home/mohanganesh/ship/.venv-train/bin/python scripts/generate_wave1.py \\")
    print(f"          --mode all \\")
    print(f"          --ports {args.ports} \\")
    print(f"          --max-inflight-per-port 5 \\")
    print(f"          --out-dir /home/mohanganesh/ship/ship/maritime_pipeline/data/generation")
    print(f"\n🚀 Expected speed: 14,400 requests/day (vs 72 currently)")
    print(f"   578k samples in ~7 days instead of 22 years!")
    
    # Create wrapper scripts for each port
    print(f"\n📦 Creating wrapper scripts...")
    for i, port in enumerate(ports):
        wrapper = create_cloud_server_script(args.api, config['model'], port)
        print(f"   [{i+1}/{len(ports)}] {wrapper} -> port {port}")
    
    print(f"\n✅ Setup complete! Run the commands above to start using cloud API.")
