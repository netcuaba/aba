import sys
import os

# Adds the project root to sys.path so we can import from main
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.insert(0, path)

from main import Base, engine

print("Initializing database...")
# Tạo bảng
Base.metadata.create_all(bind=engine)

print("Starting migrations...")

# Migration: Thêm các cột mới vào bảng accounts nếu chưa có
def migrate_accounts():
    """Thêm các cột mới vào bảng accounts nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        if 'accounts' not in inspector.get_table_names():
            print("Table accounts does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('accounts')]
        
        with engine.connect() as conn:
            if 'full_name' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN full_name VARCHAR"))
                print("Added column full_name to accounts table")
            
            if 'email' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN email VARCHAR"))
                print("Added column email to accounts table")
            
            if 'phone' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN phone VARCHAR"))
                print("Added column phone to accounts table")
            
            if 'status' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN status VARCHAR DEFAULT 'Active'"))
                conn.execute(text("UPDATE accounts SET status = 'Active' WHERE status IS NULL"))
                conn.commit()
                print("Added column status to accounts table")
            
            if 'is_locked' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN is_locked INTEGER DEFAULT 0"))
                print("Added column is_locked to accounts table")
            
            if 'locked_at' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN locked_at DATETIME"))
                print("Added column locked_at to accounts table")
            
            if 'locked_by' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN locked_by INTEGER"))
                print("Added column locked_by to accounts table")
            
            if 'last_login' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN last_login DATETIME"))
                print("Added column last_login to accounts table")
            
            if 'password_hash' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN password_hash VARCHAR"))
                conn.execute(text("UPDATE accounts SET password_hash = password WHERE password_hash IS NULL"))
                print("Added column password_hash to accounts table")
            
            if 'is_active' not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN is_active INTEGER DEFAULT 1"))
                conn.execute(text("UPDATE accounts SET is_active = 1 WHERE is_active IS NULL"))
                print("Added column is_active to accounts table")
            
            conn.commit()
            
    except Exception as e:
        print(f"Migration error for accounts: {e}")

# Migration: Thêm các cột mới vào bảng revenue_records nếu chưa có
def migrate_revenue_records():
    """Thêm các cột mới vào bảng revenue_records nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        if 'revenue_records' not in inspector.get_table_names():
            print("Table revenue_records does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('revenue_records')]
        
        new_columns = {
            'route_type': 'VARCHAR',
            'route_name': 'VARCHAR',
            'license_plate': 'VARCHAR',
            'driver_name': 'VARCHAR'
        }
        
        with engine.connect() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE revenue_records ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"Added column {col_name} to revenue_records")
                    except Exception as e:
                        print(f"Error adding column {col_name}: {e}")
                        conn.rollback()
    except Exception as e:
        print(f"Migration error: {e}")

# Migration: Thêm các cột mới vào bảng timekeeping_details nếu chưa có
def migrate_timekeeping_details():
    """Thêm các cột mới vào bảng timekeeping_details nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        if 'timekeeping_details' not in inspector.get_table_names():
            print("Table timekeeping_details does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('timekeeping_details')]
        
        new_columns = {
            'trip_code': 'VARCHAR',
            'notes': 'VARCHAR',
            'status': 'VARCHAR'
        }
        
        with engine.connect() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE timekeeping_details ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"Added column {col_name} to timekeeping_details")
                        
                        if col_name == 'status':
                            conn.execute(text("UPDATE timekeeping_details SET status = 'Onl' WHERE status IS NULL"))
                            conn.commit()
                            print(f"Set default value 'Onl' for existing rows in status column")
                    except Exception as e:
                        print(f"Error adding column {col_name}: {e}")
                        conn.rollback()
    except Exception as e:
        print(f"Migration error: {e}")

# Migration: Thêm cột update_name vào bảng route_prices nếu chưa có
def migrate_route_prices():
    """Thêm cột update_name vào bảng route_prices nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        if 'route_prices' not in inspector.get_table_names():
            print("Table route_prices does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('route_prices')]
        
        if 'update_name' not in existing_columns:
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE route_prices ADD COLUMN update_name VARCHAR"))
                    conn.commit()
                    print("Added column update_name to route_prices")
                except Exception as e:
                    print(f"Error adding column update_name: {e}")
                    conn.rollback()
    except Exception as e:
        print(f"Migration error: {e}")

# Migration: Thêm cột discount_percent vào bảng vehicle_maintenance_items nếu chưa có
def migrate_maintenance_items():
    """Thêm cột discount_percent vào bảng vehicle_maintenance_items nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        # Kiểm tra xem bảng có tồn tại không
        if 'vehicle_maintenance_items' not in inspector.get_table_names():
            print("Table vehicle_maintenance_items does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('vehicle_maintenance_items')]
        
        if 'discount_percent' not in existing_columns:
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE vehicle_maintenance_items ADD COLUMN discount_percent FLOAT DEFAULT 0"))
                    conn.commit()
                    print("Added column discount_percent to vehicle_maintenance_items")
                except Exception as e:
                    print(f"Error adding column discount_percent: {e}")
                    conn.rollback()
    except Exception as e:
        print(f"Migration error for vehicle_maintenance_items: {e}")

# Migration: Thêm code field vào roles và permissions (RBAC refactor)
# Trả về True nếu migration thành công, False nếu thất bại
def migrate_rbac_code_fields():
    """Thêm code field vào roles và permissions table"""
    from sqlalchemy import inspect, text
    
    migration_success = True
    
    try:
        inspector = inspect(engine)
        
        # Migrate roles table
        if 'roles' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('roles')]
            
            if 'code' not in existing_columns:
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        # Step 1: Add column WITHOUT UNIQUE constraint (SQLite không hỗ trợ)
                        conn.execute(text("ALTER TABLE roles ADD COLUMN code VARCHAR"))
                        
                        # Step 2: Update existing roles với code
                        conn.execute(text("UPDATE roles SET code = 'ADMIN' WHERE name = 'Super Admin' OR name = 'Admin'"))
                        conn.execute(text("UPDATE roles SET code = 'MANAGER' WHERE name = 'Admin Operations'"))
                        conn.execute(text("UPDATE roles SET code = 'USER' WHERE name = 'Viewer' OR name = 'User'"))
                        
                        trans.commit()
                        print("Added column code to roles table")
                        
                        # Step 3: Create UNIQUE INDEX sau khi đã có dữ liệu (ngoài transaction)
                        # Kiểm tra xem index đã tồn tại chưa
                        indexes = inspector.get_indexes('roles')
                        index_names = [idx['name'] for idx in indexes]
                        if 'idx_roles_code_unique' not in index_names:
                            with engine.connect() as conn2:
                                conn2.execute(text("CREATE UNIQUE INDEX idx_roles_code_unique ON roles(code)"))
                                conn2.commit()
                                print("Created UNIQUE INDEX on roles.code")
                    except Exception as e:
                        trans.rollback()
                        print(f"Error adding code to roles: {e}")
                        migration_success = False
        
        # Migrate permissions table
        if 'permissions' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('permissions')]
            
            if 'code' not in existing_columns:
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        # Step 1: Add column WITHOUT UNIQUE constraint (SQLite không hỗ trợ)
                        conn.execute(text("ALTER TABLE permissions ADD COLUMN code VARCHAR"))
                        
                        # Step 2: Update existing permissions với code (map từ page_path + action)
                        conn.execute(text("UPDATE permissions SET code = 'user.view' WHERE page_path = '/user-management' AND action = 'view' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'user.create' WHERE page_path = '/user-management' AND action = 'create' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'user.edit' WHERE page_path = '/user-management' AND action = 'update' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'user.delete' WHERE page_path = '/user-management' AND action = 'delete' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'role.view' WHERE page_path = '/role-management' AND action = 'view' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'role.create' WHERE page_path = '/role-management' AND action = 'create' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'role.edit' WHERE page_path = '/role-management' AND action = 'update' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'role.delete' WHERE page_path = '/role-management' AND action = 'delete' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'account.view' WHERE page_path = '/accounts' AND action = 'view' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'account.edit' WHERE page_path = '/accounts' AND action = 'update' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'administrative.view' WHERE page_path = '/administrative' AND action = 'view' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'administrative.create' WHERE page_path = '/administrative' AND action = 'create' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'administrative.update' WHERE page_path = '/administrative' AND action = 'update' AND code IS NULL"))
                        conn.execute(text("UPDATE permissions SET code = 'administrative.delete' WHERE page_path = '/administrative' AND action = 'delete' AND code IS NULL"))
                        
                        trans.commit()
                        print("Added column code to permissions table")
                        
                        # Step 3: Create UNIQUE INDEX sau khi đã có dữ liệu (ngoài transaction)
                        # Kiểm tra xem index đã tồn tại chưa
                        indexes = inspector.get_indexes('permissions')
                        index_names = [idx['name'] for idx in indexes]
                        if 'idx_permissions_code_unique' not in index_names:
                            with engine.connect() as conn2:
                                conn2.execute(text("CREATE UNIQUE INDEX idx_permissions_code_unique ON permissions(code)"))
                                conn2.commit()
                                print("Created UNIQUE INDEX on permissions.code")
                    except Exception as e:
                        trans.rollback()
                        print(f"Error adding code to permissions: {e}")
                        migration_success = False
        
    except Exception as e:
        print(f"Migration error for RBAC code fields: {e}")
        migration_success = False
    
    return migration_success

# Migration: Thêm các cột mới vào bảng vehicle_assignments nếu chưa có
def migrate_vehicle_assignments():
    """Thêm các cột transfer_reason và internal_note vào bảng vehicle_assignments nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        # Kiểm tra xem bảng có tồn tại không
        if 'vehicle_assignments' not in inspector.get_table_names():
            print("Table vehicle_assignments does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('vehicle_assignments')]
        
        new_columns = {
            'transfer_reason': 'VARCHAR',
            'internal_note': 'VARCHAR'
        }
        
        with engine.connect() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE vehicle_assignments ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"Added column {col_name} to vehicle_assignments")
                    except Exception as e:
                        print(f"Error adding column {col_name}: {e}")
                        conn.rollback()
    except Exception as e:
        print(f"Migration error for vehicle_assignments: {e}")

# Migration: Thêm cột social_insurance_salary vào bảng employees nếu chưa có
def migrate_employee_social_insurance_salary():
    """Thêm cột social_insurance_salary vào bảng employees nếu chưa có"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        # Kiểm tra xem bảng có tồn tại không
        if 'employees' not in inspector.get_table_names():
            print("Table employees does not exist yet, will be created by create_all")
            return
        
        existing_columns = [col['name'] for col in inspector.get_columns('employees')]
        
        if 'social_insurance_salary' not in existing_columns:
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE employees ADD COLUMN social_insurance_salary INTEGER"))
                    conn.commit()
                    print("Added column social_insurance_salary to employees")
                except Exception as e:
                    print(f"Error adding column social_insurance_salary: {e}")
                    conn.rollback()
    except Exception as e:
        print(f"Migration error for employees.social_insurance_salary: {e}")

# Migration: Thêm cột route_status vào bảng routes nếu chưa có và set mặc định ONL
def migrate_route_status():
    """Thêm cột route_status vào bảng routes nếu chưa có và set mặc định ONL cho các tuyến cũ"""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        # Kiểm tra xem bảng có tồn tại không
        if 'routes' not in inspector.get_table_names():
            print("Table routes does not exist yet, will be created by create_all")
            return True
        
        existing_columns = [col['name'] for col in inspector.get_columns('routes')]
        
        with engine.connect() as conn:
            # Thêm cột route_status nếu chưa có
            if 'route_status' not in existing_columns:
                conn.execute(text("ALTER TABLE routes ADD COLUMN route_status VARCHAR DEFAULT 'ONL'"))
                # Set mặc định ONL cho tất cả các tuyến cũ
                conn.execute(text("UPDATE routes SET route_status = 'ONL' WHERE route_status IS NULL"))
                conn.commit()
                print("Added column route_status to routes table and set default ONL for existing routes")
            else:
                # Nếu cột đã tồn tại nhưng có giá trị NULL, set mặc định ONL
                conn.execute(text("UPDATE routes SET route_status = 'ONL' WHERE route_status IS NULL"))
                conn.commit()
                print("Updated NULL route_status values to ONL")
        
        return True
    except Exception as e:
        print(f"Migration error for routes.route_status: {e}")
        return False

if __name__ == "__main__":
    migrate_accounts()
    migrate_revenue_records()
    migrate_timekeeping_details()
    migrate_route_prices()
    migrate_maintenance_items()
    migrate_rbac_code_fields()
    migrate_vehicle_assignments()
    migrate_employee_social_insurance_salary()
    migrate_route_status()
    
    print("Migrating RBAC and initializing permissions...")
    from main import SessionLocal, initialize_permissions
    db = SessionLocal()
    try:
        initialize_permissions(db)
        print("Permissions initialized successfully.")
    except Exception as e:
        print(f"Error initializing permissions: {e}")
    finally:
        db.close()
        
    print("Database initialization and migrations completed.")
