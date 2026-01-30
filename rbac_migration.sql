-- ============================================================================
-- RBAC (Role-Based Access Control) Migration Script
-- ============================================================================
-- This script creates the RBAC tables and migrates existing role data.
-- 
-- IMPORTANT: This script does NOT delete or modify existing tables.
-- It adds new RBAC tables and updates the role_permissions table structure.
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Create Roles table
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,                    -- Role name: Super Admin, Admin Operations, etc.
    description TEXT,                             -- Role description
    is_system_role INTEGER DEFAULT 0,             -- 1 if system role (cannot delete), 0 otherwise
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STEP 2: Create UserRoles junction table (many-to-many)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,                     -- FK to accounts.id
    role_id INTEGER NOT NULL,                     -- FK to roles.id
    assigned_by INTEGER,                          -- FK to accounts.id (who assigned this role)
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES accounts(id),
    UNIQUE(user_id, role_id)                      -- Prevent duplicate role assignments
);

-- ============================================================================
-- STEP 3: Update RolePermission table to use role_id instead of role string
-- ============================================================================

-- First, create new table structure
CREATE TABLE IF NOT EXISTS role_permissions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,                     -- FK to roles.id (changed from role TEXT)
    permission_id INTEGER NOT NULL,               -- FK to permissions.id
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)                -- Prevent duplicate permission assignments
);

-- Migrate existing data if role_permissions table exists
-- Note: This assumes existing role strings can be mapped to new role IDs
-- If role_permissions table doesn't exist or is empty, this will do nothing
INSERT INTO role_permissions_new (role_id, permission_id, created_at)
SELECT 
    (SELECT r.id FROM roles r WHERE r.name = rp.role LIMIT 1) AS role_id,
    rp.permission_id,
    rp.created_at
FROM role_permissions rp
WHERE EXISTS (SELECT 1 FROM roles r WHERE r.name = rp.role)
AND NOT EXISTS (
    SELECT 1 FROM role_permissions_new rpn 
    WHERE rpn.role_id = (SELECT r.id FROM roles r WHERE r.name = rp.role LIMIT 1)
    AND rpn.permission_id = rp.permission_id
);

-- Drop old table and rename new one
DROP TABLE IF EXISTS role_permissions;
ALTER TABLE role_permissions_new RENAME TO role_permissions;

-- ============================================================================
-- STEP 4: Create indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);
CREATE INDEX IF NOT EXISTS idx_permissions_page_action ON permissions(page_path, action);

-- ============================================================================
-- STEP 5: Insert default roles
-- ============================================================================

INSERT OR IGNORE INTO roles (name, description, is_system_role) VALUES
    ('Super Admin', 'Full system access with all permissions', 1),
    ('Admin Operations', 'Administrative access to operations (Trips, Vehicles, Employees)', 1),
    ('Admin Administrative', 'Administrative access to administrative functions (Reports, Settings)', 1),
    ('Viewer', 'Read-only access to all pages', 1);

-- ============================================================================
-- STEP 6: Migrate existing account roles to user_roles table
-- ============================================================================

-- Map existing account.role strings to role IDs
-- This creates user_roles entries for existing accounts
INSERT OR IGNORE INTO user_roles (user_id, role_id, assigned_at)
SELECT 
    a.id AS user_id,
    CASE 
        WHEN a.role = 'Admin' THEN (SELECT id FROM roles WHERE name = 'Super Admin' LIMIT 1)
        WHEN a.role = 'Manager' THEN (SELECT id FROM roles WHERE name = 'Admin Operations' LIMIT 1)
        WHEN a.role = 'User' THEN (SELECT id FROM roles WHERE name = 'Viewer' LIMIT 1)
        ELSE (SELECT id FROM roles WHERE name = 'Viewer' LIMIT 1)  -- Default to Viewer
    END AS role_id,
    a.created_at AS assigned_at
FROM accounts a
WHERE NOT EXISTS (
    SELECT 1 FROM user_roles ur WHERE ur.user_id = a.id
);

-- ============================================================================
-- STEP 7: Create/Update permissions for all pages
-- ============================================================================

-- Trips permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('trips.view', 'View trips', '/operations', 'view'),
    ('trips.create', 'Create trips', '/operations', 'create'),
    ('trips.update', 'Update trips', '/operations', 'update'),
    ('trips.delete', 'Delete trips', '/operations', 'delete');

-- Vehicles permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('vehicles.view', 'View vehicles', '/vehicles', 'view'),
    ('vehicles.create', 'Create vehicles', '/vehicles', 'create'),
    ('vehicles.update', 'Update vehicles', '/vehicles', 'update'),
    ('vehicles.delete', 'Delete vehicles', '/vehicles', 'delete');

-- Employees permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('employees.view', 'View employees', '/employees', 'view'),
    ('employees.create', 'Create employees', '/employees', 'create'),
    ('employees.update', 'Update employees', '/employees', 'update'),
    ('employees.delete', 'Delete employees', '/employees', 'delete');

-- Reports permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('reports.view', 'View reports', '/finance-report', 'view'),
    ('reports.create', 'Create reports', '/finance-report', 'create'),
    ('reports.update', 'Update reports', '/finance-report', 'update'),
    ('reports.delete', 'Delete reports', '/finance-report', 'delete');

-- Administrative permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('administrative.view', 'View administrative functions', '/accounts', 'view'),
    ('administrative.create', 'Create administrative records', '/accounts', 'create'),
    ('administrative.update', 'Update administrative records', '/accounts', 'update'),
    ('administrative.delete', 'Delete administrative records', '/accounts', 'delete');

-- System Settings permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('settings.view', 'View system settings', '/settings', 'view'),
    ('settings.create', 'Create system settings', '/settings', 'create'),
    ('settings.update', 'Update system settings', '/settings', 'update'),
    ('settings.delete', 'Delete system settings', '/settings', 'delete');

-- Additional page permissions
INSERT OR IGNORE INTO permissions (name, description, page_path, action) VALUES
    ('timekeeping.view', 'View timekeeping', '/timekeeping-v1', 'view'),
    ('timekeeping.create', 'Create timekeeping records', '/timekeeping-v1', 'create'),
    ('timekeeping.update', 'Update timekeeping records', '/timekeeping-v1', 'update'),
    ('timekeeping.delete', 'Delete timekeeping records', '/timekeeping-v1', 'delete'),
    ('maintenance.view', 'View maintenance', '/maintenance', 'view'),
    ('maintenance.create', 'Create maintenance records', '/maintenance', 'create'),
    ('maintenance.update', 'Update maintenance records', '/maintenance', 'update'),
    ('maintenance.delete', 'Delete maintenance records', '/maintenance', 'delete'),
    ('fuel.view', 'View fuel records', '/theo-doi-dau-v2', 'view'),
    ('fuel.create', 'Create fuel records', '/theo-doi-dau-v2', 'create'),
    ('fuel.update', 'Update fuel records', '/theo-doi-dau-v2', 'update'),
    ('fuel.delete', 'Delete fuel records', '/theo-doi-dau-v2', 'delete'),
    ('salary.view', 'View salary calculations', '/salary-calculation-v2', 'view'),
    ('salary.create', 'Create salary calculations', '/salary-calculation-v2', 'create'),
    ('salary.update', 'Update salary calculations', '/salary-calculation-v2', 'update'),
    ('salary.delete', 'Delete salary calculations', '/salary-calculation-v2', 'delete');

-- ============================================================================
-- STEP 8: Assign permissions to default roles
-- ============================================================================

-- Super Admin: All permissions
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Super Admin' LIMIT 1) AS role_id,
    p.id AS permission_id
FROM permissions p;

-- Admin Operations: Trips, Vehicles, Employees (all actions)
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Admin Operations' LIMIT 1) AS role_id,
    p.id AS permission_id
FROM permissions p
WHERE p.page_path IN ('/operations', '/vehicles', '/employees')
   OR p.name LIKE 'trips.%'
   OR p.name LIKE 'vehicles.%'
   OR p.name LIKE 'employees.%';

-- Admin Administrative: Reports, Administrative, Settings (all actions)
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Admin Administrative' LIMIT 1) AS role_id,
    p.id AS permission_id
FROM permissions p
WHERE p.page_path IN ('/finance-report', '/accounts', '/settings')
   OR p.name LIKE 'reports.%'
   OR p.name LIKE 'administrative.%'
   OR p.name LIKE 'settings.%';

-- Viewer: View permissions for all pages
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 
    (SELECT id FROM roles WHERE name = 'Viewer' LIMIT 1) AS role_id,
    p.id AS permission_id
FROM permissions p
WHERE p.action = 'view';

-- ============================================================================
-- STEP 9: Log migration completion
-- ============================================================================

INSERT OR IGNORE INTO migration_log (migration_name, status, records_migrated)
VALUES 
    ('rbac_migration', 'success', 
     (SELECT COUNT(*) FROM roles) +
     (SELECT COUNT(*) FROM user_roles) +
     (SELECT COUNT(*) FROM role_permissions) +
     (SELECT COUNT(*) FROM permissions)
    );

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- 
-- Summary:
-- - Created roles table with default roles
-- - Created user_roles junction table for many-to-many relationship
-- - Updated role_permissions to use role_id FK instead of role string
-- - Created permissions for all pages and actions
-- - Assigned permissions to default roles
-- - Migrated existing account roles to user_roles table
-- 
-- Next steps:
-- 1. Update SQLAlchemy models in main.py
-- 2. Update permission checking logic
-- 3. Create user/role management pages
-- ============================================================================

