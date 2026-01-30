# RBAC Implementation Guide

## Overview

This document describes the Role-Based Access Control (RBAC) system implementation for the transport management application.

## Architecture

### Database Schema

The RBAC system uses the following tables:

1. **roles** - Stores role definitions
   - `id` (INTEGER PRIMARY KEY)
   - `name` (TEXT UNIQUE) - Role name (e.g., "Super Admin", "Admin Operations")
   - `description` (TEXT) - Role description
   - `is_system_role` (INTEGER) - 1 for system roles (cannot delete), 0 for custom roles
   - `created_at`, `updated_at` (DATETIME)

2. **user_roles** - Many-to-many relationship between users and roles
   - `id` (INTEGER PRIMARY KEY)
   - `user_id` (INTEGER FK to accounts.id)
   - `role_id` (INTEGER FK to roles.id)
   - `assigned_by` (INTEGER FK to accounts.id)
   - `assigned_at` (DATETIME)
   - UNIQUE(user_id, role_id)

3. **permissions** - Stores permission definitions
   - `id` (INTEGER PRIMARY KEY)
   - `name` (TEXT UNIQUE) - Permission name (e.g., "trips.view", "vehicles.create")
   - `description` (TEXT)
   - `page_path` (TEXT) - Page path (e.g., "/operations", "/vehicles")
   - `action` (TEXT) - Action type: "view", "create", "update", "delete"
   - `created_at` (DATETIME)

4. **role_permissions** - Many-to-many relationship between roles and permissions
   - `id` (INTEGER PRIMARY KEY)
   - `role_id` (INTEGER FK to roles.id)
   - `permission_id` (INTEGER FK to permissions.id)
   - `created_at` (DATETIME)
   - UNIQUE(role_id, permission_id)

5. **user_permissions** - Direct user permissions (overrides role permissions)
   - `id` (INTEGER PRIMARY KEY)
   - `user_id` (INTEGER FK to accounts.id)
   - `permission_id` (INTEGER FK to permissions.id)
   - `created_at` (DATETIME)

### Default Roles

1. **Super Admin** - Full system access with all permissions
2. **Admin Operations** - Administrative access to operations (Trips, Vehicles, Employees)
3. **Admin Administrative** - Administrative access to administrative functions (Reports, Settings)
4. **Viewer** - Read-only access to all pages

### Pages and Permissions

The system defines permissions for the following pages:

- **Trips** (`/operations`) - view, create, update, delete
- **Vehicles** (`/vehicles`) - view, create, update, delete
- **Employees** (`/employees`) - view, create, update, delete
- **Reports** (`/finance-report`) - view, create, update, delete
- **Administrative** (`/accounts`) - view, create, update, delete
- **System Settings** (`/settings`) - view, create, update, delete
- **Timekeeping** (`/timekeeping-v1`) - view, create, update, delete
- **Maintenance** (`/maintenance`) - view, create, update, delete
- **Fuel** (`/theo-doi-dau-v2`) - view, create, update, delete
- **Salary** (`/salary-calculation-v2`) - view, create, update, delete

## Installation

### Step 1: Run Migration

Execute the RBAC migration SQL script:

```bash
sqlite3 transport.db < rbac_migration.sql
```

Or using Python:

```python
import sqlite3
with open('rbac_migration.sql', 'r') as f:
    conn = sqlite3.connect('transport.db')
    conn.executescript(f.read())
    conn.commit()
    conn.close()
```

### Step 2: Verify Migration

Check that tables were created:

```sql
SELECT name FROM sqlite_master WHERE type='table' AND name IN ('roles', 'user_roles', 'role_permissions', 'permissions', 'user_permissions');
```

Check default roles:

```sql
SELECT * FROM roles;
```

Check permissions:

```sql
SELECT COUNT(*) FROM permissions;
```

### Step 3: Assign Initial Roles

The migration automatically assigns roles to existing users:
- Users with `role = "Admin"` → Super Admin role
- Users with `role = "Manager"` → Admin Operations role
- Users with `role = "User"` → Viewer role

## Usage

### Backend API

#### User Management

- `GET /api/users` - List all users with their roles
- `POST /api/users/{user_id}/roles` - Assign roles to a user
  ```json
  {
    "role_ids": [1, 2, 3]
  }
  ```

#### Role Management

- `GET /api/roles` - List all roles
- `POST /api/roles` - Create a new role
  ```json
  {
    "name": "Custom Role",
    "description": "Description"
  }
  ```
- `PUT /api/roles/{role_id}` - Update a role
- `DELETE /api/roles/{role_id}` - Delete a role (cannot delete system roles)

#### Permission Management

- `GET /api/permissions` - List all permissions grouped by page
- `GET /api/roles/{role_id}/permissions` - Get permissions for a role
- `POST /api/roles/{role_id}/permissions` - Update permissions for a role
  ```json
  {
    "permission_ids": [1, 2, 3, 4]
  }
  ```

### Frontend Pages

1. **User Management** (`/user-management`)
   - View all users
   - Assign roles to users
   - Create new users

2. **Role Management** (`/role-management`)
   - View all roles
   - Create/edit/delete custom roles
   - Manage permission matrix for each role

### Permission Checking

#### In Route Handlers

Use the `require_permission` dependency:

```python
@app.get("/some-page")
async def some_page(
    current_user = Depends(require_permission("/some-page", "view"))
):
    # User has permission
    pass
```

Or use `check_permission` function:

```python
if not check_permission(db, user_id, "/some-page", "view"):
    raise HTTPException(status_code=403)
```

#### In Templates

The `has_page_access` function is available in templates:

```jinja2
{% if has_page_access(current_user.role, "/some-page", current_user.id) %}
    <!-- Show content -->
{% endif %}
```

Note: Templates use fallback logic if database is not available in context.

## Security Features

1. **API-Level Enforcement**: All API endpoints check permissions before allowing access
2. **Audit Logging**: Critical actions (user update, role change, delete) are logged to `audit_logs` table
3. **System Role Protection**: System roles cannot be deleted or modified
4. **Super Admin Override**: Super Admin role has all permissions automatically

## Migration Notes

- Existing `accounts.role` field is kept for backward compatibility
- Existing `role_permissions.role` (TEXT) is migrated to `role_permissions.role_id` (INTEGER FK)
- Existing users are automatically assigned roles based on their current `role` field
- All existing tables remain intact - no data is deleted

## Troubleshooting

### Users Cannot Access Pages

1. Check user has roles assigned: `SELECT * FROM user_roles WHERE user_id = ?`
2. Check role has permissions: `SELECT * FROM role_permissions WHERE role_id = ?`
3. Check permission exists: `SELECT * FROM permissions WHERE page_path = ? AND action = ?`

### Permission Not Working

1. Verify permission exists in database
2. Check role has the permission assigned
3. Check user has the role assigned
4. Verify Super Admin role has all permissions (should return true for any check)

### Migration Issues

If migration fails:
1. Check SQLite version (should be 3.8.0+)
2. Verify database file is writable
3. Check for existing tables that might conflict
4. Review migration log: `SELECT * FROM migration_log WHERE migration_name = 'rbac_migration'`

## Future Enhancements

- Permission inheritance (role hierarchies)
- Time-based permissions
- IP-based access restrictions
- Permission groups/templates
- Bulk role assignment

