# Hướng dẫn Deploy FastAPI lên PythonAnywhere

## ⚠️ Lưu ý quan trọng về FastAPI và PythonAnywhere

**FastAPI có thể deploy trên PythonAnywhere!** 

FastAPI là ASGI framework, trong khi PythonAnywhere mặc định hỗ trợ WSGI. Để chạy FastAPI trên PythonAnywhere, chúng ta sử dụng **Mangum** - một adapter để convert ASGI app thành WSGI application.

**Không cần chuyển sang Flask!** FastAPI hoạt động tốt trên PythonAnywhere với Mangum.

## Bước 1: Upload code lên PythonAnywhere

1. Đăng nhập vào PythonAnywhere
2. Vào tab **Files**
3. Upload toàn bộ project lên thư mục home của bạn (ví dụ: `/home/yourusername/aba-product/`)

Hoặc sử dụng Git:
```bash
cd ~
git clone https://github.com/your-repo/aba-product.git
cd aba-product
```

## Bước 2: Tạo Virtual Environment

1. Vào tab **Consoles** → tạo một **Bash console**
2. Chạy các lệnh sau:

```bash
cd ~/aba-product  # hoặc đường dẫn project của bạn
python3.10 -m venv venv  # hoặc python3.9, python3.11 tùy version PythonAnywhere hỗ trợ
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Quan trọng**: Đảm bảo `mangum` đã được cài đặt (có trong requirements.txt). Mangum là adapter để convert FastAPI (ASGI) thành WSGI application cho PythonAnywhere.

## Bước 3: Cấu hình Web App

1. Vào tab **Web**
2. Click **Add a new web app**
3. Chọn **Manual configuration**
4. Chọn Python version (khuyến nghị 3.10 hoặc 3.11)
5. Click **Next**

## Bước 4: Cấu hình WSGI file

1. Trong tab **Web**, tìm phần **WSGI configuration file**
2. Click vào file WSGI (thường là `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
3. Xóa toàn bộ nội dung và thay thế bằng:

```python
import sys
import os

# Thêm đường dẫn project
path = '/home/yourusername/aba-product'  # Thay yourusername bằng username của bạn
if path not in sys.path:
    sys.path.insert(0, path)

# Import WSGI application (đã được wrap bằng Mangum)
from wsgi import application
```

**Lưu ý**: 
- Thay `yourusername` bằng username PythonAnywhere của bạn và `aba-product` bằng tên thư mục project
- File `wsgi.py` đã được cấu hình sẵn để convert FastAPI (ASGI) thành WSGI application

## Bước 5: Cấu hình Static Files

1. Trong tab **Web**, tìm phần **Static files**
2. Thêm mapping:
   - **URL**: `/static/`
   - **Directory**: `/home/yourusername/aba-product/static/`

## Bước 6: Cấu hình Working Directory

1. Trong tab **Web**, tìm phần **Code**
2. Đảm bảo **Working directory** trỏ đến: `/home/yourusername/aba-product`

## Bước 7: Khởi tạo Database (nếu chưa có)

Trong Bash console:

```bash
cd ~/aba-product
source venv/bin/activate
python -c "from main import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Bước 8: Reload Web App

1. Quay lại tab **Web**
2. Click nút **Reload** (màu xanh) để reload web app

## Bước 9: Kiểm tra

Truy cập URL của bạn: `https://yourusername.pythonanywhere.com`

## Troubleshooting

### Lỗi Import
- Kiểm tra đường dẫn trong WSGI file đã đúng chưa
- Kiểm tra virtual environment đã activate chưa
- Kiểm tra tất cả dependencies đã cài đặt chưa

### Lỗi Static Files không load
- Kiểm tra cấu hình Static files trong tab Web
- Kiểm tra đường dẫn thư mục static đã đúng chưa

### Lỗi Database
- Kiểm tra file `transport.db` có quyền ghi không
- Nếu cần, chạy lại lệnh khởi tạo database

### Lỗi Session
- Kiểm tra SECRET_KEY đã được set (có thể set trong WSGI file hoặc environment variable)

## Cấu hình nâng cao

### Set Environment Variables

Trong WSGI file, trước dòng `from wsgi import application`, thêm:

```python
import os
os.environ['SECRET_KEY'] = 'your-secret-key-here'
```

### Custom Domain

1. Vào tab **Web**
2. Tìm phần **Domains**
3. Thêm domain của bạn
4. Cấu hình DNS trỏ về PythonAnywhere

## Lưu ý quan trọng

1. **Free account**: Có giới hạn về số lượng web app và thời gian chạy
2. **Database**: SQLite sẽ hoạt động tốt, nhưng nếu cần có thể dùng MySQL/PostgreSQL
3. **File uploads**: Đảm bảo thư mục `static/uploads/` có quyền ghi
4. **Logs**: Xem logs trong tab **Web** → **Error log** và **Server log**

## Backup

Định kỳ backup:
- File database: `transport.db`
- Thư mục `static/uploads/`
- Code (nếu chưa dùng Git)

