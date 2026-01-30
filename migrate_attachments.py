"""
Helper script to migrate file attachments from JSON strings to attachments_v2 table.
This handles JSON parsing more reliably than SQL-only approach.
"""

import sqlite3
import json
import os
from pathlib import Path

def extract_filename(file_path):
    """Extract filename from full path"""
    if not file_path:
        return ''
    return os.path.basename(file_path)

def parse_json_field(value):
    """Parse JSON field, return list of strings"""
    if not value or value == '':
        return []
    
    # Try to parse as JSON
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        elif isinstance(parsed, str):
            return [parsed]
        else:
            return []
    except (json.JSONDecodeError, TypeError):
        # Not valid JSON, treat as plain string
        return [value] if value else []

def migrate_attachments(db_path='transport.db'):
    """Migrate file attachments from JSON strings to attachments_v2"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Migrating file attachments...")
    
    # Check if attachments_v2 table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='attachments_v2'
    """)
    if not cursor.fetchone():
        print("ERROR: attachments_v2 table does not exist. Run schema_v2.sql first.")
        conn.close()
        return False
    
    migrated_count = 0
    
    # Migrate vehicle inspection_documents
    print("\n1. Migrating vehicle inspection_documents...")
    cursor.execute("SELECT id, inspection_documents, created_at FROM vehicles WHERE inspection_documents IS NOT NULL AND inspection_documents != ''")
    vehicles = cursor.fetchall()
    
    for vehicle_id, inspection_docs, created_at in vehicles:
        file_paths = parse_json_field(inspection_docs)
        for file_path in file_paths:
            # Check if already migrated
            cursor.execute("""
                SELECT COUNT(*) FROM attachments_v2 
                WHERE entity_type = 'vehicle' 
                AND entity_id = ? 
                AND file_type = 'inspection'
                AND file_path = ?
            """, (vehicle_id, file_path))
            if cursor.fetchone()[0] == 0:
                file_name = extract_filename(file_path)
                cursor.execute("""
                    INSERT INTO attachments_v2 
                    (entity_type, entity_id, file_path, file_name, file_type, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('vehicle', vehicle_id, file_path, file_name, 'inspection', created_at))
                migrated_count += 1
    
    print(f"   Migrated {migrated_count} inspection documents")
    
    # Migrate vehicle phu_hieu_files
    print("\n2. Migrating vehicle phu_hieu_files...")
    cursor.execute("SELECT id, phu_hieu_files, created_at FROM vehicles WHERE phu_hieu_files IS NOT NULL AND phu_hieu_files != ''")
    vehicles = cursor.fetchall()
    
    phu_hieu_count = 0
    for vehicle_id, phu_hieu_files, created_at in vehicles:
        file_paths = parse_json_field(phu_hieu_files)
        for file_path in file_paths:
            cursor.execute("""
                SELECT COUNT(*) FROM attachments_v2 
                WHERE entity_type = 'vehicle' 
                AND entity_id = ? 
                AND file_type = 'phu_hieu'
                AND file_path = ?
            """, (vehicle_id, file_path))
            if cursor.fetchone()[0] == 0:
                file_name = extract_filename(file_path)
                cursor.execute("""
                    INSERT INTO attachments_v2 
                    (entity_type, entity_id, file_path, file_name, file_type, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('vehicle', vehicle_id, file_path, file_name, 'phu_hieu', created_at))
                phu_hieu_count += 1
    
    print(f"   Migrated {phu_hieu_count} phu_hieu files")
    migrated_count += phu_hieu_count
    
    # Migrate employee documents
    print("\n3. Migrating employee documents...")
    cursor.execute("SELECT id, documents, created_at FROM employees WHERE documents IS NOT NULL AND documents != ''")
    employees = cursor.fetchall()
    
    employee_count = 0
    for employee_id, documents, created_at in employees:
        file_paths = parse_json_field(documents)
        for file_path in file_paths:
            cursor.execute("""
                SELECT COUNT(*) FROM attachments_v2 
                WHERE entity_type = 'employee' 
                AND entity_id = ? 
                AND file_type = 'document'
                AND file_path = ?
            """, (employee_id, file_path))
            if cursor.fetchone()[0] == 0:
                file_name = extract_filename(file_path)
                cursor.execute("""
                    INSERT INTO attachments_v2 
                    (entity_type, entity_id, file_path, file_name, file_type, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('employee', employee_id, file_path, file_name, 'document', created_at))
                employee_count += 1
    
    print(f"   Migrated {employee_count} employee documents")
    migrated_count += employee_count
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Total attachments migrated: {migrated_count}")
    return True

if __name__ == '__main__':
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'transport.db'
    success = migrate_attachments(db_path)
    sys.exit(0 if success else 1)

