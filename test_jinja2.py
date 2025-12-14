#!/usr/bin/env python3
"""
Test script to isolate the Jinja2 filter issue
"""

try:
    from fastapi.templating import Jinja2Templates
    print("✅ FastAPI Jinja2Templates imported successfully")
    
    # Create templates object
    templates = Jinja2Templates(directory="templates")
    print("✅ Templates object created successfully")
    
    # Check if env has filters attribute
    if hasattr(templates.env, 'filters'):
        print("✅ templates.env.filters exists")
    else:
        print("❌ templates.env.filters does not exist")
        print("Available attributes:", [attr for attr in dir(templates.env) if not attr.startswith('_')])
    
    # Define the filter function
    def from_json(value):
        import json
        try:
            return json.loads(value) if value else []
        except:
            return []
    
    # Try to register the filter
    try:
        templates.env.filters["from_json"] = from_json
        print("✅ Filter registered successfully")
    except Exception as e:
        print(f"❌ Error registering filter: {e}")
        print(f"Error type: {type(e)}")
    
    # Test the filter
    try:
        test_value = '["test1", "test2"]'
        result = templates.env.filters["from_json"](test_value)
        print(f"✅ Filter test successful: {result}")
    except Exception as e:
        print(f"❌ Error testing filter: {e}")
    
    # Try to render a simple template
    try:
        from fastapi import Request
        # Create a mock request object
        class MockRequest:
            def __init__(self):
                self.url = "http://localhost:8000"
                self.method = "GET"
                self.headers = {}
                self.query_params = {}
                self.path_params = {}
                self.cookies = {}
                self.client = None
                self.scope = {}
        
        mock_request = MockRequest()
        
        # Test template rendering
        response = templates.TemplateResponse("base.html", {
            "request": mock_request,
            "title": "Test"
        })
        print("✅ Template rendering test successful")
        
    except Exception as e:
        print(f"❌ Error rendering template: {e}")
        print(f"Error type: {type(e)}")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc()
