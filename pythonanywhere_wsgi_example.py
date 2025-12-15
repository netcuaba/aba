"""
File WSGI mẫu cho PythonAnywhere
Copy toàn bộ nội dung này vào file WSGI của bạn trên PythonAnywhere
Thường là: /var/www/netcuaba_pythonanywhere_com_wsgi.py
"""

import sys
import os

# ============================================
# QUAN TRỌNG: Thay đổi đường dẫn này!
# ============================================
# Thay 'netcuaba' bằng username PythonAnywhere của bạn
# Thay 'aba-product' bằng tên thư mục project của bạn
project_path = '/home/netcuaba/aba-product'  # ⚠️ SỬA ĐƯỜNG DẪN NÀY!

if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Thay đổi working directory
os.chdir(project_path)

# Import WSGI application từ file wsgi.py trong project
# File wsgi.py sẽ tự động import app từ main.py và wrap bằng Mangum
from wsgi import application

# PythonAnywhere cần biến 'application'
# application đã được định nghĩa trong wsgi.py

