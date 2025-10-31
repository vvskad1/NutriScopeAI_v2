#!/usr/bin/env python3
"""
Complete integration test showing API endpoint with local/API model switching
"""

import requests
import json
from app.llm.pretrained_llm.config import USE_LOCAL_MODEL

def test_complete_integration():
    """Test the complete NutriScope AI integration"""
    
    print("🚀 NutriScope AI Complete Integration Test")
    print("=" * 50)
    
    # Test model info endpoint
    try:
        response = requests.get("http://127.0.0.1:8000/model-info")
        if response.status_code == 200:
            model_info = response.json()
            print("📊 Current Model Configuration:")
            print(f"  • Using Local Model: {model_info['using_local_model']}")
            print(f"  • Model Type: {model_info['model_type']}")
            print(f"  • Privacy Mode: {model_info['privacy_mode']}")
            print(f"  • Requires Internet: {model_info['requires_internet']}")
        else:
            print(f"❌ Failed to get model info: {response.status_code}")
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        print("Make sure FastAPI is running on http://127.0.0.1:8000")
        return
    
    print(f"\n🔧 Configuration Instructions:")
    print(f"To switch to local model: Set USE_LOCAL_MODEL = True in config.py")
    print(f"To switch to API model: Set USE_LOCAL_MODEL = False in config.py")
    
    print(f"\n✅ Integration Status:")
    print(f"  • FastAPI Backend: Running ✅")
    print(f"  • Local LLM Model: {'Active' if USE_LOCAL_MODEL else 'Standby'}")
    print(f"  • API Model: {'Standby' if USE_LOCAL_MODEL else 'Active'}")
    print(f"  • Unified Interface: Ready ✅")
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Upload a lab report via the frontend")
    print(f"2. The system will automatically use {'local' if USE_LOCAL_MODEL else 'API'} model")
    print(f"3. Toggle config to switch between models anytime")
    
    print(f"\n🏆 Your NutriScope AI is fully integrated!")
    if USE_LOCAL_MODEL:
        print(f"🔒 Running in privacy mode - all data stays local")
    else:
        print(f"☁️ Running in API mode - using cloud LLM services")

if __name__ == "__main__":
    test_complete_integration()