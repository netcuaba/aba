# Hướng dẫn sử dụng Báo cáo Tài chính

## Tổng quan
Hệ thống đã được cập nhật với tính năng **Báo cáo Tài chính** mới, cho phép theo dõi và quản lý thu chi của doanh nghiệp vận chuyển.

## Các tính năng mới

### 1. Page Báo cáo Tổng hợp (Cập nhật)
- **Địa chỉ**: `/report`
- **Tính năng**: Hiển thị 3 card báo cáo chính:
  - ⛽ Tổng hợp đổ dầu
  - 📊 Thống kê tổng hợp  
  - 💰 **Tổng hợp báo cáo tài chính** (MỚI)

### 2. Page Tổng hợp Báo cáo Tài chính (MỚI)
- **Địa chỉ**: `/finance-report`
- **Tính năng**:
  - Bộ lọc chọn tháng/năm báo cáo
  - Bảng hiển thị chi tiết thu/chi
  - Thống kê tổng hợp (Tổng thu, Tổng chi, Lợi nhuận)
  - Xuất báo cáo Excel

## Cấu trúc dữ liệu

### Bảng FinanceRecord
```sql
- id: ID duy nhất
- date: Ngày giao dịch
- category: Danh mục (Thu/Chi)
- description: Diễn giải chi tiết
- income: Số tiền thu
- expense: Số tiền chi
- balance: Thành tiền (tự động tính)
- notes: Ghi chú
- created_at: Thời gian tạo
```

## Cách sử dụng

### 1. Truy cập Báo cáo Tài chính
1. Vào trang chủ `/`
2. Click vào menu "Báo cáo" 
3. Chọn "💰 Tổng hợp báo cáo tài chính"

### 2. Xem báo cáo theo tháng
1. Chọn tháng và năm cần xem
2. Click "🔍 Xem báo cáo"
3. Hệ thống sẽ hiển thị:
   - Bảng chi tiết thu/chi
   - Thống kê tổng hợp
   - Màu sắc phân biệt (Xanh: Dương, Đỏ: Âm)

### 3. Xuất báo cáo Excel
- Click nút "📊 Xuất báo cáo Excel"
- File sẽ được tải về với tên: `BaoCaoTaiChinh_MM_YYYY.xlsx`

### 4. Tạo dữ liệu mẫu (Để test)
- Truy cập: `/finance-report/create-sample-data`
- Hệ thống sẽ tạo 12 bản ghi mẫu cho tháng hiện tại

## Giao diện

### Bảng báo cáo
| Ngày | Danh mục | Diễn giải | Chi | Thu | Thành tiền |
|------|----------|-----------|-----|-----|------------|
| 01/01/2025 | Thu | Thu tiền vận chuyển | - | 5,000,000 ₫ | 5,000,000 ₫ |
| 02/01/2025 | Chi | Chi phí đổ dầu | 2,000,000 ₫ | - | -2,000,000 ₫ |

### Thống kê tổng hợp
- **Tổng thu**: Hiển thị màu xanh
- **Tổng chi**: Hiển thị màu đỏ  
- **Lợi nhuận**: Xanh nếu dương, đỏ nếu âm

## Lưu ý kỹ thuật

### Database
- Bảng `finance_records` sẽ được tạo tự động khi chạy ứng dụng
- Dữ liệu được lưu trữ trong SQLite database

### API Endpoints
- `GET /finance-report`: Hiển thị trang báo cáo
- `GET /finance-report/export`: Xuất Excel
- `GET /finance-report/create-sample-data`: Tạo dữ liệu mẫu

### Responsive Design
- Giao diện tương thích với mobile
- Bảng có thể cuộn ngang trên màn hình nhỏ

## Mở rộng trong tương lai
- Thêm chức năng nhập dữ liệu tài chính
- Báo cáo theo quý/năm
- Biểu đồ thống kê
- Tích hợp với các module khác (đổ dầu, lương...)
