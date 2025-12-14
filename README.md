# 🚛 Hệ thống quản lý vận chuyển

Hệ thống quản lý vận chuyển được xây dựng với FastAPI backend và HTML/CSS frontend, sử dụng SQLite database để lưu trữ dữ liệu.

## ✨ Tính năng chính

- 👥 **Quản lý nhân viên**: Thêm, sửa, xóa (soft delete) thông tin nhân viên, CCCD, bằng lái xe và upload giấy tờ
- 🚚 **Quản lý xe**: Thêm, sửa, xóa (soft delete) thông tin xe, biển số, trọng tải và tiêu hao nhiên liệu
- 🛣️ **Quản lý tuyến**: Thêm, sửa, xóa (soft delete) tuyến đường, khoảng cách, đơn giá và phân công xe
- 📅 **Ghi nhận chuyến hàng ngày**: Ghi nhận chuyến hàng hàng ngày với số km, tải trọng, lái xe và biển số
- 📊 **Thống kê hoạt động**: Báo cáo thống kê hoạt động vận chuyển theo nhân viên

## 🛠️ Công nghệ sử dụng

- **Backend**: Python FastAPI
- **Frontend**: HTML + CSS (Jinja2 templates)
- **Database**: SQLite
- **Styling**: CSS Grid, Flexbox với gradient và glassmorphism effects

## 📦 Cài đặt

1. **Clone repository**:
```bash
git clone <repository-url>
cd transport-management
```

2. **Cài đặt dependencies**:
```bash
pip install -r requirements.txt
```

3. **Chạy ứng dụng**:
```bash
python main.py
```

4. **Truy cập ứng dụng**:
Mở trình duyệt và truy cập: `http://localhost:8000`

## 📁 Cấu trúc project

```
transport-management/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── README.md              # Documentation
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Trang chủ
│   ├── employees.html    # Quản lý nhân viên
│   ├── vehicles.html     # Quản lý xe
│   ├── routes.html       # Quản lý tuyến
│   ├── daily.html        # Ghi nhận chuyến hàng ngày
│   └── salary.html       # Tính lương
├── static/               # Static files
│   └── style.css        # CSS styling
└── transport.db         # SQLite database (tự động tạo)
```

## 🗄️ Database Schema

### Employees (Nhân viên)
- `id`: Primary key
- `name`: Họ tên nhân viên
- `phone`: Số điện thoại
- `cccd`: Số CCCD
- `cccd_expiry`: Ngày hết hạn CCCD
- `driving_license`: Số bằng lái xe
- `license_expiry`: Ngày hết hạn bằng lái
- `documents`: Đường dẫn file giấy tờ
- `status`: Trạng thái (1: Hoạt động, 0: Đã xóa)
- `created_at`: Ngày tạo

### Vehicles (Xe)
- `id`: Primary key
- `license_plate`: Biển số xe
- `capacity`: Trọng tải (kg)
- `fuel_consumption`: Tiêu hao nhiên liệu (lít/100km)
- `status`: Trạng thái (1: Hoạt động, 0: Đã xóa)
- `created_at`: Ngày tạo

### Routes (Tuyến đường)
- `id`: Primary key
- `route_code`: Mã tuyến (VD: NA_002)
- `route_name`: Tên tuyến
- `distance`: Khoảng cách (km)
- `unit_price`: Đơn giá (VNĐ/km)
- `vehicle_id`: ID xe phụ trách
- `is_active`: Trạng thái hoạt động
- `status`: Trạng thái (1: Hoạt động, 0: Đã xóa)
- `created_at`: Ngày tạo

### DailyRoutes (Chuyến hàng ngày)
- `id`: Primary key
- `route_id`: ID tuyến
- `date`: Ngày chạy
- `distance_km`: Số km thực tế
- `cargo_weight`: Tải trọng (kg)
- `driver_name`: Tên lái xe
- `license_plate`: Biển số xe thực tế
- `employee_name`: Tên nhân viên phụ trách
- `notes`: Ghi chú
- `created_at`: Ngày tạo

## 📊 Thống kê hoạt động

Hệ thống cung cấp báo cáo thống kê chi tiết về hoạt động vận chuyển:

- **Số chuyến**: Tổng số chuyến vận chuyển mỗi nhân viên đã thực hiện
- **Tổng số km**: Tổng quãng đường thực tế đã chạy
- **Tổng tải trọng**: Tổng trọng lượng hàng hóa đã vận chuyển
- **Các tuyến**: Danh sách mã tuyến nhân viên đã chạy

## 🗑️ Soft Delete

Hệ thống sử dụng **Soft Delete** cho tất cả các thực thể:
- Khi "xóa" nhân viên, xe, hoặc tuyến, hệ thống chỉ cập nhật trạng thái `status = 0`
- Dữ liệu không bị xóa thật khỏi database
- Đảm bảo tính toàn vẹn dữ liệu và có thể khôi phục khi cần
- Chỉ hiển thị các bản ghi có `status = 1` (đang hoạt động)

## 🎯 Hướng dẫn sử dụng

1. **Thêm nhân viên**: Vào mục "Nhân viên" để thêm thông tin nhân viên, CCCD, bằng lái xe và upload giấy tờ
2. **Thêm xe**: Vào mục "Xe" để thêm thông tin xe và biển số
3. **Thiết lập tuyến**: Vào mục "Tuyến đường" để tạo tuyến và phân công xe
4. **Ghi nhận chuyến**: Mỗi ngày vào mục "Chuyến hàng ngày" để ghi nhận chuyến với số km, tải trọng, lái xe
5. **Xem thống kê**: Vào mục "Thống kê" để xem báo cáo hoạt động vận chuyển theo nhân viên

## 🔧 API Endpoints

- `GET /`: Trang chủ
- `GET /employees`: Danh sách nhân viên
- `POST /employees/add`: Thêm nhân viên
- `GET /employees/edit/{id}`: Sửa nhân viên
- `POST /employees/edit/{id}`: Cập nhật nhân viên
- `POST /employees/delete/{id}`: Xóa nhân viên (soft delete)
- `GET /vehicles`: Danh sách xe
- `POST /vehicles/add`: Thêm xe
- `GET /vehicles/edit/{id}`: Sửa xe
- `POST /vehicles/edit/{id}`: Cập nhật xe
- `POST /vehicles/delete/{id}`: Xóa xe (soft delete)
- `GET /routes`: Danh sách tuyến
- `POST /routes/add`: Thêm tuyến
- `GET /routes/edit/{id}`: Sửa tuyến
- `POST /routes/edit/{id}`: Cập nhật tuyến
- `POST /routes/delete/{id}`: Xóa tuyến (soft delete)
- `GET /daily`: Chuyến hàng ngày
- `POST /daily/add`: Ghi nhận chuyến
- `GET /salary`: Thống kê hoạt động

## 📱 Responsive Design

Ứng dụng được thiết kế responsive, hoạt động tốt trên:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (< 768px)

## 🎨 UI/UX Features

- **Modern Design**: Sử dụng gradient và glassmorphism effects
- **Responsive Layout**: CSS Grid và Flexbox
- **Interactive Elements**: Hover effects và smooth transitions
- **Color Coding**: Mã màu cho các trạng thái khác nhau
- **Statistics Cards**: Hiển thị thống kê tổng quan
- **Form Validation**: Validation phía client và server

## 🚀 Deployment

Để deploy lên production:

1. **Cài đặt production dependencies**:
```bash
pip install gunicorn
```

2. **Chạy với Gunicorn**:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

3. **Cấu hình reverse proxy** (Nginx):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết.
