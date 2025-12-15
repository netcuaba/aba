# 🔧 Sửa lỗi WSGI trên PythonAnywhere

## ❌ Lỗi hiện tại

```
ModuleNotFoundError: No module named 'app'
File "/var/www/netcuaba_pythonanywhere_com_wsgi.py", line 117
    from app import app
```

## ✅ Giải pháp

File WSGI trên PythonAnywhere đang cố import từ `app` module, nhưng project này dùng `main.py`.

### Cách sửa:

1. **Vào PythonAnywhere Dashboard**
   - Tab **Web**
   - Tìm phần **WSGI configuration file**
   - Click vào file: `/var/www/netcuaba_pythonanywhere_com_wsgi.py`

2. **Xóa toàn bộ nội dung cũ**

3. **Copy code này vào (NHỚ SỬA ĐƯỜNG DẪN!):**

```python
import sys
import os

# ⚠️ QUAN TRỌNG: Sửa đường dẫn này!
# Thay 'netcuaba' bằng username của bạn
# Thay 'aba-product' bằng tên thư mục project của bạn
project_path = '/home/netcuaba/aba-product'

if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.chdir(project_path)

# Import từ wsgi.py (file này sẽ import app từ main.py)
from wsgi import application
```

4. **Lưu file**

5. **Reload web app** (click nút Reload màu xanh)

## 🔍 Kiểm tra đường dẫn

Nếu không chắc đường dẫn project:
1. Vào tab **Files**
2. Tìm thư mục project
3. Click chuột phải → Copy path
4. Dán vào `project_path` trong WSGI file

## 📝 Giải thích

- Project dùng `main.py` chứ không phải `app.py`
- File `wsgi.py` trong project đã được cấu hình sẵn:
  - Import `app` từ `main.py`
  - Wrap bằng Mangum để convert ASGI → WSGI
- File WSGI trên PythonAnywhere chỉ cần import từ `wsgi.py`

## ✅ Sau khi sửa

Reload web app và kiểm tra:
- Website: `https://netcuaba.pythonanywhere.com`
- Nếu vẫn lỗi, xem **Error log** trong tab Web

