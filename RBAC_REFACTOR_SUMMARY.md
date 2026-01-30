# RBAC Refactor Summary - Chuẩn hóa RBAC System

## Tổng quan

Đã refactor toàn bộ hệ thống RBAC để chuẩn hóa theo mô hình User → Role → Permission với permission codes thay vì hard-coded role checks.

## Những thay đổi chính

### 1. Database Schema Updates

#### Models đã cập nhật:
- **Role**: Thêm field `code` (ADMIN, MANAGER, USER...)
- **Permission**: Thêm field `code` (user.view, user.edit, role.manage...) - PRIMARY identifier
- **Account**: 
  - Thêm field `password_hash` (chuẩn RBAC)
  - Thêm field `is_active` (chuẩn RBAC)
  - Giữ `password` và `role` cho backward compatibility

#### Cấu trúc bảng chuẩn:
```
users (accounts)
  - id, username, password_hash, is_active, created_at

roles
  - id, code, name, description

permissions
  - id, code, name, description, page_path, action

user_roles
  - user_id, role_id

role_permissions
  - role_id, permission_id
```

### 2. Permission System

#### Permission Codes chuẩn:
- **User Management**: `user.view`, `user.create`, `user.edit`, `user.delete`, `user.manage`
- **Role Management**: `role.view`, `role.create`, `role.edit`, `role.delete`, `role.manage`
- **Permission Management**: `permission.view`, `permission.assign`, `permission.manage`
- **Account (Personal)**: `account.view`, `account.edit`
- **Operations**: `operations.view`, `employee.*`, `vehicle.*`, `route.*`
- **Other Features**: `timekeeping.view`, `maintenance.view`, `fuel.view`, `salary.view`, `finance.view`, `administrative.*`

#### Mapping Page → Permission:
- `/accounts` → `account.view` (thông tin cá nhân)
- `/user-management` → `user.view` (quản lý users)
- `/role-management` → `role.view` (quản lý roles)
- `/permission-management` → `permission.view` (phân quyền)

### 3. Backend Changes

#### Functions đã refactor:
- `check_permission()`: Chuyển từ `(page_path, action)` sang `(permission_code)` làm PRIMARY method
- `require_permission()`: Dependency hỗ trợ cả `permission_code` và legacy `page_path + action`
- `has_page_access()`: Template helper tự động map page_path → permission_code
- `get_user_permissions()`: Trả về dict với key là `permission_code`

#### Routes đã cập nhật:
- `/accounts`: Chuyển thành trang thông tin cá nhân (mọi user đều có)
- `/user-management`: CRUD users, gán roles → `user.view`, `user.create`, `user.edit`, `user.delete`
- `/role-management`: CRUD roles → `role.view`, `role.create`, `role.edit`, `role.delete`
- `/permission-management`: Gán permissions cho roles → `permission.view`, `permission.assign`
- Tất cả API routes đã chuyển sang dùng `permission_code`

### 4. Frontend Changes

#### Menu Updates:
- **Tài khoản**: Hiển thị cho mọi user (thông tin cá nhân)
- **QL Người dùng**: Chỉ hiển thị nếu có `user.view`
- **QL Vai trò**: Chỉ hiển thị nếu có `role.view`
- **Phân quyền**: Chỉ hiển thị nếu có `permission.view`

#### Pages:
- `account.html`: Hiển thị thông tin cá nhân + roles + permissions
- `user_management.html`: CRUD users, gán roles
- `role_management.html`: CRUD roles
- `permission_management.html`: Gán permissions cho roles (MỚI)

### 5. Migration Script

File: `rbac_refactor_migration.sql`

#### Nội dung:
1. Thêm `code` field vào `roles` và `permissions`
2. Seed permissions chuẩn với codes
3. Gán tất cả permissions cho ADMIN role
4. Đảm bảo admin users có ADMIN role
5. Tạo indexes cho performance

## Cách sử dụng

### 1. Chạy Migration

```bash
sqlite3 transport.db < rbac_refactor_migration.sql
```

Hoặc chạy từ Python:
```python
import sqlite3
conn = sqlite3.connect('transport.db')
with open('rbac_refactor_migration.sql', 'r') as f:
    conn.executescript(f.read())
conn.close()
```

### 2. Kiểm tra sau migration

```sql
-- Kiểm tra ADMIN role có đầy đủ permissions
SELECT COUNT(*) FROM role_permissions rp 
JOIN roles r ON rp.role_id = r.id 
WHERE r.code = 'ADMIN';

-- Kiểm tra admin user có ADMIN role
SELECT a.username, r.code, r.name FROM accounts a
JOIN user_roles ur ON a.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE a.role = 'Admin' OR a.role = 'Super Admin';
```

### 3. Sử dụng trong Code

#### Backend:
```python
# Check permission
if check_permission(db, user_id, "user.view"):
    # Allow access

# Dependency
@app.get("/users")
async def users(current_user = Depends(require_permission("user.view"))):
    ...
```

#### Frontend Template:
```jinja2
{% if has_page_access(current_user.role, "/user-management", current_user.id) %}
    <!-- Show menu -->
{% endif %}
```

## Phân biệt các Pages

| Page | Chức năng | Permission Required |
|------|-----------|---------------------|
| `/accounts` | Thông tin cá nhân user đang đăng nhập | `account.view` (mọi user) |
| `/user-management` | CRUD users, gán roles cho users | `user.view`, `user.create`, `user.edit`, `user.delete` |
| `/role-management` | CRUD roles | `role.view`, `role.create`, `role.edit`, `role.delete` |
| `/permission-management` | Gán permissions cho roles | `permission.view`, `permission.assign` |

## Lưu ý quan trọng

1. **Backward Compatibility**: 
   - Vẫn hỗ trợ `page_path + action` trong `check_permission()` nhưng khuyến khích dùng `permission_code`
   - Legacy `role` field trong `accounts` vẫn được giữ

2. **Admin Role**:
   - Role với `code = 'ADMIN'` tự động có tất cả permissions
   - Không cần hard-code checks `role == "Admin"` nữa

3. **Security**:
   - Deny by default: Nếu permission không được định nghĩa, access bị deny (không còn allow mặc định)
   - Tất cả routes đều check permissions, không còn hard-coded role checks

4. **Migration**:
   - Chạy migration script trước khi deploy
   - Đảm bảo admin user có ADMIN role với đầy đủ permissions

## Kết quả mong muốn

✅ User admin truy cập được toàn bộ page quản trị  
✅ Không còn access-denied sai logic  
✅ Hệ thống RBAC rõ ràng, dễ mở rộng  
✅ UI menu & backend permission đồng bộ 100%  
✅ Không hard-code quyền trong code  
✅ Mọi kiểm tra truy cập dựa trên `permission.code`

## Troubleshooting

### Admin user vẫn bị access-denied:
1. Kiểm tra user có ADMIN role: `SELECT * FROM user_roles WHERE user_id = ?`
2. Kiểm tra ADMIN role có permissions: `SELECT COUNT(*) FROM role_permissions WHERE role_id = (SELECT id FROM roles WHERE code = 'ADMIN')`
3. Chạy lại migration script nếu cần

### Menu không hiển thị:
1. Kiểm tra permission code mapping trong `PAGE_PERMISSION_MAP`
2. Kiểm tra user có permission: `get_user_permissions(db, user_id)`
3. Kiểm tra template có truyền `db` vào `has_page_access()`

