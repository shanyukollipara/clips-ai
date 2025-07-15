#!/usr/bin/env python3
"""
Test script to verify Gemini API with the new model
"""
import os
import requests
import json

def test_gemini_api():
    # Get API key from environment
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not found")
        return False
    
    print(f"🔑 Testing Gemini API with key: {api_key[:10]}...")
    
    # Test API with a simple prompt
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hello! Please respond with 'API test successful' to confirm you're working."
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 100,
        }
    }
    
    try:
        response = requests.post(
            f"{api_url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        print(f"📡 API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ API test successful!")
                print(f"📝 Response: {content}")
                return True
            else:
                print("❌ No content in response")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Gemini API Test")
    print("=" * 40)
    
    success = test_gemini_api()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Gemini API test completed successfully")
    else:
        print("❌ Gemini API test failed")
        print("\n💡 To fix:")
        print("1. Check your GEMINI_API_KEY environment variable")
        print("2. Verify the API key has the right permissions")
        print("3. Make sure the model is available and not overloaded") 