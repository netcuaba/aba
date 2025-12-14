#!/usr/bin/env python3
"""
Script test để kiểm tra endpoint driver details
"""

import requests
import json
from datetime import datetime, date

def test_driver_details_endpoint():
    """Test endpoint /salary/driver-details-page/{driver_name}"""
    
    base_url = "http://localhost:8000"
    
    # Test 1: Kiểm tra trang salary chính
    print("=== Test 1: Kiểm tra trang salary chính ===")
    try:
        response = requests.get(f"{base_url}/salary")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Trang salary tải thành công")
            # Kiểm tra xem có chứa link đến trang chi tiết không
            if "driver-details-page" in response.text:
                print("✅ Link đến trang chi tiết đã được thêm vào")
            else:
                print("❌ Link đến trang chi tiết chưa được thêm vào")
        else:
            print(f"❌ Lỗi tải trang: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Không thể kết nối đến server. Vui lòng chạy server trước.")
        return
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    # Test 2: Kiểm tra trang chi tiết lái xe
    print("\n=== Test 2: Kiểm tra trang chi tiết lái xe ===")
    try:
        response = requests.get(f"{base_url}/salary/driver-details-page/Test%20Driver")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Trang chi tiết lái xe tải thành công")
            # Kiểm tra xem có chứa thông tin cần thiết không
            if "Chi tiết chuyến" in response.text and "Test Driver" in response.text:
                print("✅ Nội dung trang chi tiết hiển thị đúng")
            else:
                print("❌ Nội dung trang chi tiết không đúng")
        else:
            print(f"❌ Lỗi tải trang chi tiết: {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    # Test 3: Kiểm tra trang chi tiết với khoảng thời gian
    print("\n=== Test 3: Kiểm tra trang chi tiết với khoảng thời gian ===")
    try:
        from_date = "2024-01-01"
        to_date = "2024-12-31"
        response = requests.get(f"{base_url}/salary/driver-details-page/Test%20Driver?from_date={from_date}&to_date={to_date}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Trang chi tiết với khoảng thời gian tải thành công")
        else:
            print(f"❌ Lỗi tải trang chi tiết với khoảng thời gian: {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    # Test 4: Kiểm tra API endpoint cũ (vẫn hoạt động)
    print("\n=== Test 4: Kiểm tra API endpoint cũ ===")
    try:
        response = requests.get(f"{base_url}/salary/driver-details/Test%20Driver")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ API endpoint cũ vẫn hoạt động")
            data = response.json()
            if "trip_details" in data:
                print("✅ API trả về đúng format")
            else:
                print("❌ API không trả về đúng format")
        else:
            print(f"❌ Lỗi API endpoint cũ: {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    test_driver_details_endpoint()
