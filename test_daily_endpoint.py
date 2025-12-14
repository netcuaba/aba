#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import sys

try:
    # Test the daily endpoint
    response = requests.get('http://localhost:8000/daily')
    
    if response.status_code == 200:
        print("✅ Daily page accessible")
        print(f"Response length: {len(response.text)} characters")
        
        # Check if vehicles data is in the response
        if "50H-147.40" in response.text:
            print("✅ Vehicle data found in response")
        else:
            print("❌ Vehicle data NOT found in response")
            
        # Check debug info
        if "Số xe:" in response.text:
            print("✅ Debug info present in response")
        else:
            print("❌ Debug info NOT found")
            
    else:
        print(f"❌ Error accessing daily page: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server. Is it running on http://localhost:8000?")
except Exception as e:
    print(f"❌ Error: {e}")
