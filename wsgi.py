"""
WSGI entry point cho PythonAnywhere
File này được sử dụng bởi PythonAnywhere để chạy FastAPI app
FastAPI là ASGI app, cần adapter để chạy trên WSGI server của PythonAnywhere
"""
import sys
import os

# Thêm đường dẫn project vào Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# Import app từ main.py
from main import app

# Sử dụng Mangum để convert ASGI app (FastAPI) thành WSGI application
# Mangum là adapter phổ biến nhất để chạy FastAPI trên WSGI servers
try:
    from mangum import Mangum
    # Mangum wrap FastAPI app thành WSGI-compatible
    # lifespan="off" vì PythonAnywhere WSGI không hỗ trợ lifespan events
    application = Mangum(app, lifespan="off")
except ImportError:
    # Fallback: nếu không có mangum, thử dùng asgiref (ít phổ biến hơn)
    try:
        from asgiref.wsgi import WsgiToAsgi
        application = WsgiToAsgi(app)
    except ImportError:
        # Nếu cả hai đều không có, raise error với hướng dẫn rõ ràng
        raise ImportError(
            "❌ Cần cài đặt mangum để chạy FastAPI trên PythonAnywhere!\n\n"
            "FastAPI là ASGI framework, PythonAnywhere dùng WSGI server.\n"
            "Mangum giúp convert ASGI → WSGI.\n\n"
            "👉 Chạy lệnh: pip install mangum\n"
            "Hoặc: pip install -r requirements.txt"
        )

