"""
Migration Verification Script
Verifies that V2 migration completed successfully and data integrity is maintained.
"""

import sqlite3
import sys
from datetime import datetime

def verify_migration(db_path='transport.db'):
    """Verify migration completeness and data integrity"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("MIGRATION VERIFICATION REPORT")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    issues = []
    warnings = []
    
    # 1. Check if V2 tables exist
    print("1. Checking V2 tables exist...")
    v2_tables = [
        'trips_v2',
        'fuel_records_v2',
        'finance_transactions_v2',
        'timekeeping_details_v2',
        'daily_prices_v2',
        'attachments_v2',
        'migration_log'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    for table in v2_tables:
        if table in existing_tables:
            print(f"   ✓ {table} exists")
        else:
            print(f"   ✗ {table} MISSING")
            issues.append(f"Table {table} does not exist")
    
    print()
    
    # 2. Check record counts
    print("2. Checking record counts...")
    
    # Daily routes vs trips_v2
    cursor.execute("SELECT COUNT(*) FROM daily_routes")
    daily_routes_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM trips_v2")
    trips_v2_count = cursor.fetchone()[0]
    
    print(f"   daily_routes (V1): {daily_routes_count:,}")
    print(f"   trips_v2 (V2): {trips_v2_count:,}")
    
    if trips_v2_count == 0:
        issues.append("trips_v2 is empty - migration may have failed")
    elif trips_v2_count < daily_routes_count * 0.9:  # Allow 10% difference due to merges
        warnings.append(f"trips_v2 has significantly fewer records than daily_routes ({trips_v2_count} vs {daily_routes_count})")
    
    # Revenue records
    cursor.execute("SELECT COUNT(*) FROM revenue_records")
    revenue_count = cursor.fetchone()[0]
    print(f"   revenue_records (V1): {revenue_count:,}")
    
    # Fuel records
    cursor.execute("SELECT COUNT(*) FROM fuel_records")
    fuel_v1_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM fuel_records_v2")
    fuel_v2_count = cursor.fetchone()[0]
    print(f"   fuel_records (V1): {fuel_v1_count:,}")
    print(f"   fuel_records_v2 (V2): {fuel_v2_count:,}")
    
    if fuel_v2_count == 0 and fuel_v1_count > 0:
        issues.append("fuel_records_v2 is empty but fuel_records has data")
    
    # Finance transactions
    cursor.execute("SELECT COUNT(*) FROM finance_transactions")
    ft_v1_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM finance_transactions_v2")
    ft_v2_count = cursor.fetchone()[0]
    print(f"   finance_transactions (V1): {ft_v1_count:,}")
    print(f"   finance_transactions_v2 (V2): {ft_v2_count:,}")
    
    print()
    
    # 3. Check foreign key integrity
    print("3. Checking foreign key integrity...")
    
    # Trips with invalid route_id
    cursor.execute("""
        SELECT COUNT(*) FROM trips_v2 t
        LEFT JOIN routes r ON r.id = t.route_id
        WHERE t.route_id IS NOT NULL AND r.id IS NULL
    """)
    invalid_routes = cursor.fetchone()[0]
    if invalid_routes > 0:
        issues.append(f"{invalid_routes} trips_v2 records have invalid route_id")
        print(f"   ✗ {invalid_routes} trips with invalid route_id")
    else:
        print(f"   ✓ All trips have valid route_id")
    
    # Trips with invalid vehicle_id
    cursor.execute("""
        SELECT COUNT(*) FROM trips_v2 t
        LEFT JOIN vehicles v ON v.id = t.vehicle_id
        WHERE t.vehicle_id IS NOT NULL AND v.id IS NULL
    """)
    invalid_vehicles = cursor.fetchone()[0]
    if invalid_vehicles > 0:
        warnings.append(f"{invalid_vehicles} trips_v2 records have invalid vehicle_id (may be historical data)")
        print(f"   ⚠ {invalid_vehicles} trips with invalid vehicle_id (may be OK for historical data)")
    else:
        print(f"   ✓ All trips have valid vehicle_id")
    
    # Trips with invalid driver_id
    cursor.execute("""
        SELECT COUNT(*) FROM trips_v2 t
        LEFT JOIN employees e ON e.id = t.driver_id
        WHERE t.driver_id IS NOT NULL AND e.id IS NULL
    """)
    invalid_drivers = cursor.fetchone()[0]
    if invalid_drivers > 0:
        warnings.append(f"{invalid_drivers} trips_v2 records have invalid driver_id (may be historical data)")
        print(f"   ⚠ {invalid_drivers} trips with invalid driver_id (may be OK for historical data)")
    else:
        print(f"   ✓ All trips have valid driver_id")
    
    # Fuel records with invalid vehicle_id
    cursor.execute("""
        SELECT COUNT(*) FROM fuel_records_v2 fr
        LEFT JOIN vehicles v ON v.id = fr.vehicle_id
        WHERE fr.vehicle_id IS NOT NULL AND v.id IS NULL
    """)
    invalid_fuel_vehicles = cursor.fetchone()[0]
    if invalid_fuel_vehicles > 0:
        issues.append(f"{invalid_fuel_vehicles} fuel_records_v2 have invalid vehicle_id")
        print(f"   ✗ {invalid_fuel_vehicles} fuel records with invalid vehicle_id")
    else:
        print(f"   ✓ All fuel records have valid vehicle_id")
    
    print()
    
    # 4. Check indexes
    print("4. Checking indexes...")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='trips_v2'")
    trip_indexes = [row[0] for row in cursor.fetchall()]
    
    required_indexes = [
        'idx_trips_v2_date',
        'idx_trips_v2_route_id',
        'idx_trips_v2_vehicle_id',
        'idx_trips_v2_driver_id'
    ]
    
    for idx in required_indexes:
        if idx in trip_indexes:
            print(f"   ✓ {idx} exists")
        else:
            warnings.append(f"Index {idx} missing")
            print(f"   ⚠ {idx} missing")
    
    print()
    
    # 5. Check migration log
    print("5. Checking migration log...")
    
    cursor.execute("SELECT * FROM migration_log ORDER BY executed_at DESC LIMIT 1")
    log_entry = cursor.fetchone()
    
    if log_entry:
        migration_name, executed_at, status, records_migrated, error_message = log_entry
        print(f"   Migration: {migration_name}")
        print(f"   Executed: {executed_at}")
        print(f"   Status: {status}")
        print(f"   Records migrated: {records_migrated:,}")
        if error_message:
            issues.append(f"Migration log shows error: {error_message}")
            print(f"   ✗ Error: {error_message}")
        elif status != 'success':
            issues.append(f"Migration status is '{status}', not 'success'")
            print(f"   ✗ Status is '{status}'")
        else:
            print(f"   ✓ Migration completed successfully")
    else:
        warnings.append("No migration log entry found")
        print(f"   ⚠ No migration log entry")
    
    print()
    
    # 6. Check data consistency
    print("6. Checking data consistency...")
    
    # Check for duplicate trips (same route, date, vehicle)
    cursor.execute("""
        SELECT route_id, date, vehicle_id, COUNT(*) as cnt
        FROM trips_v2
        WHERE vehicle_id IS NOT NULL
        GROUP BY route_id, date, vehicle_id
        HAVING cnt > 1
        LIMIT 10
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        warnings.append(f"Found {len(duplicates)} potential duplicate trips")
        print(f"   ⚠ Found {len(duplicates)} potential duplicate trips (may be intentional)")
        for dup in duplicates[:5]:
            print(f"      Route {dup[0]}, Date {dup[1]}, Vehicle {dup[2]}: {dup[3]} trips")
    else:
        print(f"   ✓ No duplicate trips found")
    
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if issues:
        print(f"\n❌ ISSUES FOUND ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if not issues and not warnings:
        print("\n✅ Migration verification PASSED - No issues found!")
        return 0
    elif not issues:
        print("\n⚠️  Migration verification PASSED with warnings")
        return 0
    else:
        print("\n❌ Migration verification FAILED - Please review issues above")
        return 1
    
    conn.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'transport.db'
    exit_code = verify_migration(db_path)
    sys.exit(exit_code)

