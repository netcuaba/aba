-- ============================================================================
-- SQLite Database Migration Script: V1 to V2
-- ============================================================================
-- This script migrates data from denormalized V1 tables to normalized V2 tables.
-- 
-- IMPORTANT: This script does NOT delete or modify existing V1 tables.
-- Both V1 and V2 tables will coexist for backward compatibility.
-- 
-- Migration Strategy:
-- 1. Create V2 tables (if not exists)
-- 2. Migrate data with proper FK resolution
-- 3. Handle missing references gracefully
-- 4. Log migration progress
-- ============================================================================

-- Begin transaction for atomic migration
BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Create V2 tables (if schema_v2.sql hasn't been run)
-- ============================================================================

-- Note: Run schema_v2.sql first, or include CREATE TABLE statements here
-- For brevity, assuming schema_v2.sql has been executed

-- ============================================================================
-- STEP 2: Helper function to resolve vehicle_id from license_plate
-- ============================================================================

-- SQLite doesn't support stored functions, so we'll use subqueries
-- Create a temporary view for easier reference
CREATE TEMP VIEW IF NOT EXISTS vehicle_lookup AS
SELECT id, license_plate FROM vehicles;

-- ============================================================================
-- STEP 3: Helper function to resolve employee_id from driver_name
-- ============================================================================

CREATE TEMP VIEW IF NOT EXISTS employee_lookup AS
SELECT id, name FROM employees;

-- ============================================================================
-- STEP 4: Migrate daily_routes to trips_v2
-- ============================================================================

INSERT INTO trips_v2 (
    route_id,
    vehicle_id,
    driver_id,
    date,
    distance_km,
    cargo_weight,
    trip_code,
    status,
    notes,
    created_at,
    updated_at
)
SELECT 
    dr.route_id,
    (SELECT v.id FROM vehicles v WHERE v.license_plate = dr.license_plate LIMIT 1) AS vehicle_id,
    (SELECT e.id FROM employees e WHERE e.name = dr.driver_name LIMIT 1) AS driver_id,
    dr.date,
    dr.distance_km,
    dr.cargo_weight,
    NULL AS trip_code,
    CASE 
        WHEN dr.status = 'Online' OR dr.status = 'ON' OR dr.status = 'Onl' THEN 1
        WHEN dr.status = 'OFF' OR dr.status = 'Offline' THEN 0
        ELSE 1  -- Default to Online
    END AS status,
    dr.notes,
    dr.created_at,
    COALESCE(dr.updated_at, dr.created_at) AS updated_at
FROM daily_routes dr
WHERE NOT EXISTS (
    SELECT 1 FROM trips_v2 t 
    WHERE t.route_id = dr.route_id 
    AND t.date = dr.date
    AND t.vehicle_id = (SELECT v.id FROM vehicles v WHERE v.license_plate = dr.license_plate LIMIT 1)
);

-- ============================================================================
-- STEP 5: Migrate revenue_records to trips_v2 (merge with existing trips)
-- ============================================================================

-- First, insert revenue_records that don't have matching trips_v2
INSERT INTO trips_v2 (
    route_id,
    vehicle_id,
    driver_id,
    date,
    distance_km,
    unit_price,
    bridge_fee,
    loading_fee,
    late_penalty,
    total_amount,
    manual_total,
    itinerary,
    status,
    notes,
    created_at,
    updated_at
)
SELECT 
    rr.route_id,
    (SELECT v.id FROM vehicles v WHERE v.license_plate = rr.license_plate LIMIT 1) AS vehicle_id,
    (SELECT e.id FROM employees e WHERE e.name = rr.driver_name LIMIT 1) AS driver_id,
    rr.date,
    rr.distance_km,
    rr.unit_price,
    rr.bridge_fee,
    rr.loading_fee,
    rr.late_penalty,
    rr.total_amount,
    rr.manual_total,
    rr.route_name AS itinerary,
    CASE 
        WHEN rr.status = 'Online' OR rr.status = 'ON' THEN 1
        WHEN rr.status = 'Offline' OR rr.status = 'OFF' THEN 0
        ELSE 1
    END AS status,
    rr.notes,
    rr.created_at,
    COALESCE(rr.updated_at, rr.created_at) AS updated_at
FROM revenue_records rr
WHERE NOT EXISTS (
    SELECT 1 FROM trips_v2 t 
    WHERE t.route_id = rr.route_id 
    AND t.date = rr.date
    AND t.vehicle_id = (SELECT v.id FROM vehicles v WHERE v.license_plate = rr.license_plate LIMIT 1)
);

-- Update existing trips_v2 with revenue data where matches exist
UPDATE trips_v2 SET
    unit_price = (
        SELECT rr.unit_price FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ),
    bridge_fee = (
        SELECT rr.bridge_fee FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ),
    loading_fee = (
        SELECT rr.loading_fee FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ),
    late_penalty = (
        SELECT rr.late_penalty FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ),
    total_amount = COALESCE((
        SELECT rr.total_amount FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ), trips_v2.total_amount),
    manual_total = COALESCE((
        SELECT rr.manual_total FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ), trips_v2.manual_total),
    itinerary = COALESCE((
        SELECT rr.route_name FROM revenue_records rr
        WHERE rr.route_id = trips_v2.route_id
        AND rr.date = trips_v2.date
        AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
        LIMIT 1
    ), trips_v2.itinerary)
WHERE EXISTS (
    SELECT 1 FROM revenue_records rr
    WHERE rr.route_id = trips_v2.route_id
    AND rr.date = trips_v2.date
    AND rr.license_plate = (SELECT v.license_plate FROM vehicles v WHERE v.id = trips_v2.vehicle_id LIMIT 1)
);

-- ============================================================================
-- STEP 6: Migrate fuel_records to fuel_records_v2
-- ============================================================================

INSERT INTO fuel_records_v2 (
    vehicle_id,
    date,
    fuel_type,
    fuel_price_per_liter,
    liters_pumped,
    cost_pumped,
    trip_id,
    notes,
    created_at
)
SELECT 
    (SELECT v.id FROM vehicles v WHERE v.license_plate = fr.license_plate LIMIT 1) AS vehicle_id,
    fr.date,
    fr.fuel_type,
    CAST(fr.fuel_price_per_liter AS INTEGER) AS fuel_price_per_liter,
    fr.liters_pumped,
    CAST(fr.cost_pumped AS INTEGER) AS cost_pumped,
    NULL AS trip_id,  -- Can be linked later if needed
    fr.notes,
    fr.created_at
FROM fuel_records fr
WHERE EXISTS (
    SELECT 1 FROM vehicles v WHERE v.license_plate = fr.license_plate
)
AND NOT EXISTS (
    SELECT 1 FROM fuel_records_v2 fr2
    WHERE fr2.vehicle_id = (SELECT v.id FROM vehicles v WHERE v.license_plate = fr.license_plate LIMIT 1)
    AND fr2.date = fr.date
    AND fr2.liters_pumped = fr.liters_pumped
);

-- ============================================================================
-- STEP 7: Migrate finance_transactions to finance_transactions_v2
-- ============================================================================

INSERT INTO finance_transactions_v2 (
    transaction_type,
    category,
    date,
    route_id,
    trip_id,
    description,
    amount,
    vat_rate,
    discount1_rate,
    discount2_rate,
    total_amount,
    notes,
    created_at,
    updated_at
)
SELECT 
    CASE 
        WHEN ft.transaction_type = 'Thu' OR ft.transaction_type = 'Income' THEN 1
        WHEN ft.transaction_type = 'Chi' OR ft.transaction_type = 'Expense' THEN 0
        ELSE 0
    END AS transaction_type,
    ft.category,
    ft.date,
    (SELECT r.id FROM routes r WHERE r.route_code = ft.route_code LIMIT 1) AS route_id,
    NULL AS trip_id,  -- Can be linked later if needed
    ft.description,
    CAST(ft.amount AS INTEGER) AS amount,
    ft.vat AS vat_rate,
    ft.discount1 AS discount1_rate,
    ft.discount2 AS discount2_rate,
    CAST(ft.total AS INTEGER) AS total_amount,
    ft.note AS notes,
    ft.created_at,
    COALESCE(ft.updated_at, ft.created_at) AS updated_at
FROM finance_transactions ft
WHERE NOT EXISTS (
    SELECT 1 FROM finance_transactions_v2 ft2
    WHERE ft2.date = ft.date
    AND ft2.description = ft.description
    AND ft2.amount = CAST(ft.amount AS INTEGER)
);

-- ============================================================================
-- STEP 8: Migrate finance_records to finance_transactions_v2
-- ============================================================================

-- Migrate income records
INSERT INTO finance_transactions_v2 (
    transaction_type,
    category,
    date,
    route_id,
    trip_id,
    description,
    amount,
    vat_rate,
    discount1_rate,
    discount2_rate,
    total_amount,
    notes,
    created_at,
    updated_at
)
SELECT 
    1 AS transaction_type,  -- Income
    fr.category,
    fr.date,
    (SELECT r.id FROM routes r WHERE r.route_code = fr.route_code LIMIT 1) AS route_id,
    NULL AS trip_id,
    fr.description,
    CAST(fr.amount_before_vat AS INTEGER) AS amount,
    fr.vat_rate,
    fr.discount1_rate,
    fr.discount2_rate,
    CAST(fr.final_amount AS INTEGER) AS total_amount,
    fr.notes,
    fr.created_at,
    fr.created_at AS updated_at
FROM finance_records fr
WHERE fr.income > 0 OR fr.final_amount > 0
AND NOT EXISTS (
    SELECT 1 FROM finance_transactions_v2 ft2
    WHERE ft2.date = fr.date
    AND ft2.description = fr.description
    AND ft2.transaction_type = 1
);

-- Migrate expense records
INSERT INTO finance_transactions_v2 (
    transaction_type,
    category,
    date,
    route_id,
    trip_id,
    description,
    amount,
    vat_rate,
    discount1_rate,
    discount2_rate,
    total_amount,
    notes,
    created_at,
    updated_at
)
SELECT 
    0 AS transaction_type,  -- Expense
    fr.category,
    fr.date,
    (SELECT r.id FROM routes r WHERE r.route_code = fr.route_code LIMIT 1) AS route_id,
    NULL AS trip_id,
    fr.description,
    CAST(fr.amount_before_vat AS INTEGER) AS amount,
    fr.vat_rate,
    fr.discount1_rate,
    fr.discount2_rate,
    CAST(fr.final_amount AS INTEGER) AS total_amount,
    fr.notes,
    fr.created_at,
    fr.created_at AS updated_at
FROM finance_records fr
WHERE fr.expense > 0
AND NOT EXISTS (
    SELECT 1 FROM finance_transactions_v2 ft2
    WHERE ft2.date = fr.date
    AND ft2.description = fr.description
    AND ft2.transaction_type = 0
);

-- ============================================================================
-- STEP 9: Migrate timekeeping_details to timekeeping_details_v2
-- ============================================================================

-- First, migrate timekeeping_tables
INSERT INTO timekeeping_tables_v2 (id, name, from_date, to_date, created_at)
SELECT id, name, from_date, to_date, created_at
FROM timekeeping_tables
WHERE NOT EXISTS (
    SELECT 1 FROM timekeeping_tables_v2 tt2 WHERE tt2.id = timekeeping_tables.id
);

-- Migrate timekeeping_details (link to trips_v2)
INSERT INTO timekeeping_details_v2 (
    table_id,
    trip_id,
    sheet_name,
    notes,
    created_at,
    updated_at
)
SELECT 
    td.table_id,
    (SELECT t.id FROM trips_v2 t
     WHERE t.route_id = (SELECT r.id FROM routes r WHERE r.route_code = td.route_code OR r.route_name = td.route_name LIMIT 1)
     AND t.date = td.date
     AND t.vehicle_id = (SELECT v.id FROM vehicles v WHERE v.license_plate = td.license_plate LIMIT 1)
     LIMIT 1) AS trip_id,
    td.sheet_name,
    td.notes,
    td.created_at,
    COALESCE(td.updated_at, td.created_at) AS updated_at
FROM timekeeping_details td
WHERE EXISTS (
    SELECT 1 FROM trips_v2 t
    WHERE t.route_id = (SELECT r.id FROM routes r WHERE r.route_code = td.route_code OR r.route_name = td.route_name LIMIT 1)
    AND t.date = td.date
    AND t.vehicle_id = (SELECT v.id FROM vehicles v WHERE v.license_plate = td.license_plate LIMIT 1)
)
AND NOT EXISTS (
    SELECT 1 FROM timekeeping_details_v2 td2 WHERE td2.id = td.id
);

-- ============================================================================
-- STEP 10: Migrate daily_prices to daily_prices_v2
-- ============================================================================

INSERT INTO daily_prices_v2 (
    date,
    route_id,
    standard_km,
    actual_km,
    purchase_price,
    selling_price,
    purchase_amount,
    selling_amount,
    created_at,
    updated_at
)
SELECT 
    dp.date,
    dp.route_id,  -- Already has route_id
    dp.standard_km,
    dp.actual_km,
    dp.purchase_price,
    dp.selling_price,
    dp.purchase_amount,
    dp.selling_amount,
    dp.created_at,
    COALESCE(dp.updated_at, dp.created_at) AS updated_at
FROM daily_prices dp
WHERE NOT EXISTS (
    SELECT 1 FROM daily_prices_v2 dp2
    WHERE dp2.date = dp.date
    AND dp2.route_id = dp.route_id
);

-- ============================================================================
-- STEP 11: Migrate file attachments (from JSON strings to attachments_v2)
-- ============================================================================
-- Note: File attachment migration is complex due to JSON parsing requirements.
-- For better reliability, use the Python script migrate_attachments.py instead:
--   python migrate_attachments.py transport.db
--
-- If you prefer SQL-only migration, uncomment the following section.
-- However, it requires SQLite JSON1 extension and may not work on all systems.

-- SQL-only migration (commented out - use Python script instead)
/*
-- Simple migration: treat each field as single file path
-- For JSON arrays, use migrate_attachments.py instead

INSERT INTO attachments_v2 (
    entity_type, entity_id, file_path, file_name, file_type, uploaded_at
)
SELECT 
    'vehicle', id, inspection_documents, 
    SUBSTR(inspection_documents, LENGTH(inspection_documents) - INSTR(REVERSE(inspection_documents), '/') + 2),
    'inspection', created_at
FROM vehicles 
WHERE inspection_documents IS NOT NULL AND inspection_documents != ''
AND NOT EXISTS (
    SELECT 1 FROM attachments_v2 a2 
    WHERE a2.entity_type = 'vehicle' AND a2.entity_id = vehicles.id AND a2.file_type = 'inspection'
);

INSERT INTO attachments_v2 (
    entity_type, entity_id, file_path, file_name, file_type, uploaded_at
)
SELECT 
    'vehicle', id, phu_hieu_files,
    SUBSTR(phu_hieu_files, LENGTH(phu_hieu_files) - INSTR(REVERSE(phu_hieu_files), '/') + 2),
    'phu_hieu', created_at
FROM vehicles 
WHERE phu_hieu_files IS NOT NULL AND phu_hieu_files != ''
AND NOT EXISTS (
    SELECT 1 FROM attachments_v2 a2 
    WHERE a2.entity_type = 'vehicle' AND a2.entity_id = vehicles.id AND a2.file_type = 'phu_hieu'
);

INSERT INTO attachments_v2 (
    entity_type, entity_id, file_path, file_name, file_type, uploaded_at
)
SELECT 
    'employee', id, documents,
    SUBSTR(documents, LENGTH(documents) - INSTR(REVERSE(documents), '/') + 2),
    'document', created_at
FROM employees 
WHERE documents IS NOT NULL AND documents != ''
AND NOT EXISTS (
    SELECT 1 FROM attachments_v2 a2 
    WHERE a2.entity_type = 'employee' AND a2.entity_id = employees.id AND a2.file_type = 'document'
);
*/

-- ============================================================================
-- STEP 12: Log migration completion
-- ============================================================================

INSERT INTO migration_log (migration_name, status, records_migrated)
VALUES 
    ('migrate_to_v2', 'success', 
     (SELECT COUNT(*) FROM trips_v2) +
     (SELECT COUNT(*) FROM fuel_records_v2) +
     (SELECT COUNT(*) FROM finance_transactions_v2) +
     (SELECT COUNT(*) FROM timekeeping_details_v2) +
     (SELECT COUNT(*) FROM daily_prices_v2) +
     (SELECT COUNT(*) FROM attachments_v2)
    );

-- Commit transaction
COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- 
-- Summary:
-- - trips_v2: Core table consolidating daily_routes, revenue_records, timekeeping_details
-- - fuel_records_v2: Normalized with vehicle_id FK
-- - finance_transactions_v2: Normalized with route_id FK
-- - timekeeping_details_v2: Links to trips_v2
-- - daily_prices_v2: Normalized with route_id FK
-- - attachments_v2: Generic file metadata storage
-- 
-- All V1 tables remain intact for backward compatibility.
-- ============================================================================

