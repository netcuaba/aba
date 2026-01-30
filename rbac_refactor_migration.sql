-- ============================================================================
-- RBAC Refactor Migration Script
-- Chuẩn hóa RBAC: thêm code fields và seed permissions theo chuẩn
-- ============================================================================
-- Mục tiêu:
-- 1. Thêm code field vào roles và permissions
-- 2. Seed permissions chuẩn với code (user.view, user.edit, role.manage...)
-- 3. Đảm bảo ADMIN role có đầy đủ permissions
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Thêm code field vào roles table và password_hash vào accounts
-- ============================================================================
ALTER TABLE roles ADD COLUMN code TEXT UNIQUE;

-- Thêm password_hash và is_active vào accounts (nếu chưa có)
ALTER TABLE accounts ADD COLUMN password_hash TEXT;
ALTER TABLE accounts ADD COLUMN is_active INTEGER DEFAULT 1;

-- Copy password sang password_hash cho các accounts hiện có (backward compatibility)
UPDATE accounts SET password_hash = password WHERE password_hash IS NULL;
UPDATE accounts SET is_active = 1 WHERE is_active IS NULL;

-- Update existing roles với code
UPDATE roles SET code = 'ADMIN' WHERE name = 'Super Admin' OR name = 'Admin';
UPDATE roles SET code = 'MANAGER' WHERE name = 'Admin Operations';
UPDATE roles SET code = 'USER' WHERE name = 'Viewer' OR name = 'User';

-- Tạo ADMIN role nếu chưa có
INSERT OR IGNORE INTO roles (code, name, description, is_system_role) 
VALUES ('ADMIN', 'Admin', 'Quản trị viên hệ thống - có đầy đủ quyền', 1);

-- ============================================================================
-- STEP 2: Thêm code field vào permissions table
-- ============================================================================
ALTER TABLE permissions ADD COLUMN code TEXT UNIQUE;

-- ============================================================================
-- STEP 3: Seed permissions chuẩn với code
-- ============================================================================

-- User Management Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('user.view', 'user.view', 'Xem danh sách người dùng', '/user-management', 'view'),
('user.create', 'user.create', 'Tạo người dùng mới', '/user-management', 'create'),
('user.edit', 'user.edit', 'Chỉnh sửa thông tin người dùng', '/user-management', 'update'),
('user.delete', 'user.delete', 'Xóa người dùng', '/user-management', 'delete'),
('user.manage', 'user.manage', 'Quản lý người dùng (tất cả quyền)', '/user-management', 'manage');

-- Role Management Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('role.view', 'role.view', 'Xem danh sách vai trò', '/role-management', 'view'),
('role.create', 'role.create', 'Tạo vai trò mới', '/role-management', 'create'),
('role.edit', 'role.edit', 'Chỉnh sửa vai trò', '/role-management', 'update'),
('role.delete', 'role.delete', 'Xóa vai trò', '/role-management', 'delete'),
('role.manage', 'role.manage', 'Quản lý vai trò (tất cả quyền)', '/role-management', 'manage');

-- Permission Management Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('permission.view', 'permission.view', 'Xem danh sách quyền', '/permission-management', 'view'),
('permission.assign', 'permission.assign', 'Gán quyền cho vai trò', '/permission-management', 'update'),
('permission.manage', 'permission.manage', 'Quản lý phân quyền (tất cả quyền)', '/permission-management', 'manage');

-- Account (Personal) Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('account.view', 'account.view', 'Xem thông tin tài khoản cá nhân', '/accounts', 'view'),
('account.edit', 'account.edit', 'Chỉnh sửa thông tin tài khoản cá nhân', '/accounts', 'update');

-- Operations Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('operations.view', 'operations.view', 'Xem trang quản lý vận hành', '/operations', 'view'),
('employee.view', 'employee.view', 'Xem danh sách nhân viên', '/employees', 'view'),
('employee.create', 'employee.create', 'Tạo nhân viên mới', '/employees', 'create'),
('employee.edit', 'employee.edit', 'Chỉnh sửa nhân viên', '/employees', 'update'),
('employee.delete', 'employee.delete', 'Xóa nhân viên', '/employees', 'delete'),
('vehicle.view', 'vehicle.view', 'Xem danh sách xe', '/vehicles', 'view'),
('vehicle.create', 'vehicle.create', 'Tạo xe mới', '/vehicles', 'create'),
('vehicle.edit', 'vehicle.edit', 'Chỉnh sửa xe', '/vehicles', 'update'),
('vehicle.delete', 'vehicle.delete', 'Xóa xe', '/vehicles', 'delete'),
('route.view', 'route.view', 'Xem danh sách tuyến', '/routes', 'view'),
('route.create', 'route.create', 'Tạo tuyến mới', '/routes', 'create'),
('route.edit', 'route.edit', 'Chỉnh sửa tuyến', '/routes', 'update'),
('route.delete', 'route.delete', 'Xóa tuyến', '/routes', 'delete');

-- Other Feature Permissions
INSERT OR IGNORE INTO permissions (code, name, description, page_path, action) VALUES
('timekeeping.view', 'timekeeping.view', 'Xem bảng chấm công', '/timekeeping-v1', 'view'),
('maintenance.view', 'maintenance.view', 'Xem bảo dưỡng xe', '/maintenance', 'view'),
('fuel.view', 'fuel.view', 'Xem theo dõi dầu', '/theo-doi-dau-v2', 'view'),
('salary.view', 'salary.view', 'Xem tính lương', '/salary-calculation-v2', 'view'),
('finance.view', 'finance.view', 'Xem báo cáo tài chính', '/finance-report', 'view'),
('revenue.view', 'revenue.view', 'Xem doanh thu', '/revenue', 'view'),
('daily.view', 'daily.view', 'Xem chuyến hàng ngày', '/daily-new', 'view'),
('administrative.view', 'administrative.view', 'Xem quản lý hành chính', '/administrative', 'view'),
('administrative.create', 'administrative.create', 'Tạo tài liệu hành chính', '/administrative', 'create'),
('administrative.update', 'administrative.update', 'Cập nhật tài liệu hành chính', '/administrative', 'update'),
('administrative.delete', 'administrative.delete', 'Xóa tài liệu hành chính', '/administrative', 'delete'),
('home.view', 'home.view', 'Xem trang chủ', '/', 'view');

-- Update existing permissions với code (nếu chưa có)
-- Map từ page_path + action sang code
UPDATE permissions SET code = 'user.view' WHERE page_path = '/user-management' AND action = 'view' AND code IS NULL;
UPDATE permissions SET code = 'user.create' WHERE page_path = '/user-management' AND action = 'create' AND code IS NULL;
UPDATE permissions SET code = 'user.edit' WHERE page_path = '/user-management' AND action = 'update' AND code IS NULL;
UPDATE permissions SET code = 'user.delete' WHERE page_path = '/user-management' AND action = 'delete' AND code IS NULL;
UPDATE permissions SET code = 'role.view' WHERE page_path = '/role-management' AND action = 'view' AND code IS NULL;
UPDATE permissions SET code = 'role.create' WHERE page_path = '/role-management' AND action = 'create' AND code IS NULL;
UPDATE permissions SET code = 'role.edit' WHERE page_path = '/role-management' AND action = 'update' AND code IS NULL;
UPDATE permissions SET code = 'role.delete' WHERE page_path = '/role-management' AND action = 'delete' AND code IS NULL;
UPDATE permissions SET code = 'account.view' WHERE page_path = '/accounts' AND action = 'view' AND code IS NULL;
UPDATE permissions SET code = 'account.edit' WHERE page_path = '/accounts' AND action = 'update' AND code IS NULL;
UPDATE permissions SET code = 'administrative.view' WHERE page_path = '/administrative' AND action = 'view' AND code IS NULL;
UPDATE permissions SET code = 'administrative.create' WHERE page_path = '/administrative' AND action = 'create' AND code IS NULL;
UPDATE permissions SET code = 'administrative.update' WHERE page_path = '/administrative' AND action = 'update' AND code IS NULL;
UPDATE permissions SET code = 'administrative.delete' WHERE page_path = '/administrative' AND action = 'delete' AND code IS NULL;

-- ============================================================================
-- STEP 4: Gán tất cả permissions cho ADMIN role
-- ============================================================================

-- Lấy ADMIN role ID
-- Gán tất cả permissions cho ADMIN role
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 
    r.id AS role_id,
    p.id AS permission_id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'ADMIN'
AND NOT EXISTS (
    SELECT 1 FROM role_permissions rp 
    WHERE rp.role_id = r.id AND rp.permission_id = p.id
);

-- ============================================================================
-- STEP 5: Đảm bảo admin user có ADMIN role
-- ============================================================================

-- Tìm user có role = "Admin" hoặc "Super Admin" trong accounts table
-- Gán ADMIN role cho họ
INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_at)
SELECT 
    a.id AS user_id,
    r.id AS role_id,
    CURRENT_TIMESTAMP AS assigned_at
FROM accounts a
CROSS JOIN roles r
WHERE (a.role = 'Admin' OR a.role = 'Super Admin')
AND r.code = 'ADMIN'
AND NOT EXISTS (
    SELECT 1 FROM user_roles ur 
    WHERE ur.user_id = a.id AND ur.role_id = r.id
);

-- ============================================================================
-- STEP 6: Tạo indexes cho performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code);
CREATE INDEX IF NOT EXISTS idx_roles_code ON roles(code);

COMMIT;

-- ============================================================================
-- Verification queries (chạy sau khi migration xong)
-- ============================================================================
-- Kiểm tra ADMIN role có đầy đủ permissions:
-- SELECT COUNT(*) FROM role_permissions rp 
-- JOIN roles r ON rp.role_id = r.id 
-- WHERE r.code = 'ADMIN';
--
-- Kiểm tra admin user có ADMIN role:
-- SELECT a.username, r.code, r.name FROM accounts a
-- JOIN user_roles ur ON a.id = ur.user_id
-- JOIN roles r ON ur.role_id = r.id
-- WHERE a.role = 'Admin' OR a.role = 'Super Admin';

