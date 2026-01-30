-- ============================================================================
-- SQLite Database Schema V2 - Optimized and Normalized
-- ============================================================================
-- This schema introduces normalized tables with INTEGER foreign keys,
-- eliminating duplicated TEXT fields and improving performance.
-- 
-- Key Improvements:
-- 1. Single core 'trips' table replaces daily_routes, revenue_records, timekeeping_details
-- 2. INTEGER foreign keys instead of duplicated TEXT (license_plate, driver_name, route_code)
-- 3. INTEGER enum values for status fields instead of TEXT
-- 4. Generic attachments table for file metadata (no files in DB)
-- 5. Proper indexes on frequently queried columns
-- ============================================================================

-- ============================================================================
-- ENUM VALUE TABLES (Reference tables for status values)
-- ============================================================================

-- Trip status enum: 0=Offline, 1=Online
-- Account status enum: 0=Inactive, 1=Active
-- Employee status enum: 0=Resigned, 1=Active, 2=LongLeave
-- Transaction type enum: 0=Expense, 1=Income
-- Route type enum: 0=NoiThanh, 1=NoiTinh, 2=LienTinh, 3=TangCuongNoiTinh, 4=TangCuongLienTinh

-- ============================================================================
-- CORE TRIPS TABLE (Replaces daily_routes, revenue_records, timekeeping_details)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trips_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core trip identification
    route_id INTEGER NOT NULL,                    -- FK to routes.id
    vehicle_id INTEGER,                            -- FK to vehicles.id (nullable for historical data)
    driver_id INTEGER,                             -- FK to employees.id (nullable for historical data)
    date DATE NOT NULL,                            -- Trip date
    
    -- Trip details
    distance_km REAL DEFAULT 0,                   -- Distance in km
    cargo_weight REAL DEFAULT 0,                   -- Cargo weight
    trip_code TEXT,                                -- Trip code (optional)
    itinerary TEXT,                                -- Route itinerary (for enhanced routes)
    
    -- Pricing (can override route defaults)
    unit_price INTEGER DEFAULT 0,                 -- Unit price (VNĐ/km)
    bridge_fee INTEGER DEFAULT 0,                 -- Bridge fee (VNĐ)
    loading_fee INTEGER DEFAULT 0,                -- Loading fee (VNĐ)
    late_penalty INTEGER DEFAULT 0,               -- Late penalty (VNĐ)
    
    -- Revenue calculation
    total_amount INTEGER DEFAULT 0,               -- Calculated total
    manual_total INTEGER DEFAULT 0,               -- Manual override total
    
    -- Status and metadata
    status INTEGER DEFAULT 1,                     -- 0=Offline, 1=Online
    notes TEXT,                                    -- Notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    FOREIGN KEY (route_id) REFERENCES routes(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (driver_id) REFERENCES employees(id)
);

-- Indexes for trips_v2
CREATE INDEX IF NOT EXISTS idx_trips_v2_date ON trips_v2(date);
CREATE INDEX IF NOT EXISTS idx_trips_v2_route_id ON trips_v2(route_id);
CREATE INDEX IF NOT EXISTS idx_trips_v2_vehicle_id ON trips_v2(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_trips_v2_driver_id ON trips_v2(driver_id);
CREATE INDEX IF NOT EXISTS idx_trips_v2_date_route ON trips_v2(date, route_id);

-- ============================================================================
-- TRIP COSTS TABLE (For fuel and other trip-related costs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trip_costs_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    trip_id INTEGER NOT NULL,                     -- FK to trips_v2.id
    cost_type INTEGER NOT NULL,                    -- 0=Fuel, 1=Maintenance, 2=Other
    date DATE NOT NULL,                            -- Cost date
    
    -- Cost details
    description TEXT NOT NULL,                     -- Cost description
    amount INTEGER NOT NULL DEFAULT 0,            -- Amount (VNĐ)
    vat_rate REAL DEFAULT 0,                      -- VAT rate (%)
    discount1_rate REAL DEFAULT 0,                -- Discount 1 (%)
    discount2_rate REAL DEFAULT 0,                -- Discount 2 (%)
    total_amount INTEGER DEFAULT 0,               -- Total after VAT/discounts
    
    notes TEXT,                                    -- Notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (trip_id) REFERENCES trips_v2(id)
);

-- Indexes for trip_costs_v2
CREATE INDEX IF NOT EXISTS idx_trip_costs_v2_trip_id ON trip_costs_v2(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_costs_v2_date ON trip_costs_v2(date);
CREATE INDEX IF NOT EXISTS idx_trip_costs_v2_cost_type ON trip_costs_v2(cost_type);

-- ============================================================================
-- FUEL RECORDS V2 (Normalized with vehicle_id FK)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fuel_records_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    vehicle_id INTEGER NOT NULL,                   -- FK to vehicles.id
    date DATE NOT NULL,                            -- Fuel date
    
    -- Fuel details
    fuel_type TEXT DEFAULT 'Dầu DO 0,05S-II',     -- Fuel type
    fuel_price_per_liter INTEGER DEFAULT 0,       -- Price per liter (VNĐ)
    liters_pumped REAL DEFAULT 0,                 -- Liters pumped
    cost_pumped INTEGER DEFAULT 0,                -- Total cost (VNĐ)
    
    -- Optional trip linkage
    trip_id INTEGER,                               -- FK to trips_v2.id (if linked to specific trip)
    
    notes TEXT,                                    -- Notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (trip_id) REFERENCES trips_v2(id)
);

-- Indexes for fuel_records_v2
CREATE INDEX IF NOT EXISTS idx_fuel_records_v2_vehicle_id ON fuel_records_v2(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_fuel_records_v2_date ON fuel_records_v2(date);
CREATE INDEX IF NOT EXISTS idx_fuel_records_v2_trip_id ON fuel_records_v2(trip_id);

-- ============================================================================
-- FINANCE TRANSACTIONS V2 (Normalized with route_id FK)
-- ============================================================================

CREATE TABLE IF NOT EXISTS finance_transactions_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    transaction_type INTEGER NOT NULL,             -- 0=Expense, 1=Income
    category TEXT NOT NULL,                        -- Category name
    date DATE NOT NULL,                            -- Transaction date
    
    -- Optional trip/route linkage
    route_id INTEGER,                               -- FK to routes.id
    trip_id INTEGER,                               -- FK to trips_v2.id (if linked to specific trip)
    
    -- Transaction details
    description TEXT NOT NULL,                     -- Description
    amount INTEGER DEFAULT 0,                     -- Amount before VAT (VNĐ)
    vat_rate REAL DEFAULT 0,                      -- VAT rate (%)
    discount1_rate REAL DEFAULT 0,                -- Discount 1 (%)
    discount2_rate REAL DEFAULT 0,                -- Discount 2 (%)
    total_amount INTEGER DEFAULT 0,               -- Total amount (VNĐ)
    
    notes TEXT,                                    -- Notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (route_id) REFERENCES routes(id),
    FOREIGN KEY (trip_id) REFERENCES trips_v2(id)
);

-- Indexes for finance_transactions_v2
CREATE INDEX IF NOT EXISTS idx_finance_transactions_v2_date ON finance_transactions_v2(date);
CREATE INDEX IF NOT EXISTS idx_finance_transactions_v2_route_id ON finance_transactions_v2(route_id);
CREATE INDEX IF NOT EXISTS idx_finance_transactions_v2_trip_id ON finance_transactions_v2(trip_id);
CREATE INDEX IF NOT EXISTS idx_finance_transactions_v2_type ON finance_transactions_v2(transaction_type);

-- ============================================================================
-- ATTACHMENTS TABLE (Generic file metadata storage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS attachments_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Entity linkage (polymorphic)
    entity_type TEXT NOT NULL,                     -- 'vehicle', 'employee', 'maintenance', 'trip', etc.
    entity_id INTEGER NOT NULL,                    -- ID of the entity
    
    -- File metadata
    file_path TEXT NOT NULL,                       -- Relative path to file
    file_name TEXT NOT NULL,                       -- Original filename
    file_size INTEGER,                             -- File size in bytes
    mime_type TEXT,                                -- MIME type
    file_type TEXT,                                -- 'insurance', 'registration', 'photo', 'document', etc.
    
    -- Metadata
    description TEXT,                               -- Description
    uploaded_by INTEGER,                           -- FK to accounts.id
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (uploaded_by) REFERENCES accounts(id)
);

-- Indexes for attachments_v2
CREATE INDEX IF NOT EXISTS idx_attachments_v2_entity ON attachments_v2(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attachments_v2_file_type ON attachments_v2(file_type);

-- ============================================================================
-- TIMEKEEPING V2 (Normalized version)
-- ============================================================================

CREATE TABLE IF NOT EXISTS timekeeping_tables_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                            -- Timekeeping table name
    from_date DATE NOT NULL,                       -- Start date
    to_date DATE NOT NULL,                         -- End date
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timekeeping_details_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    table_id INTEGER NOT NULL,                     -- FK to timekeeping_tables_v2.id
    trip_id INTEGER NOT NULL,                      -- FK to trips_v2.id (links to core trip)
    
    sheet_name TEXT NOT NULL,                      -- Sheet name
    notes TEXT,                                    -- Additional notes
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (table_id) REFERENCES timekeeping_tables_v2(id),
    FOREIGN KEY (trip_id) REFERENCES trips_v2(id)
);

-- Indexes for timekeeping_details_v2
CREATE INDEX IF NOT EXISTS idx_timekeeping_details_v2_table_id ON timekeeping_details_v2(table_id);
CREATE INDEX IF NOT EXISTS idx_timekeeping_details_v2_trip_id ON timekeeping_details_v2(trip_id);

-- ============================================================================
-- DAILY PRICES V2 (Normalized with route_id FK)
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_prices_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    date DATE NOT NULL,
    route_id INTEGER NOT NULL,                     -- FK to routes.id (replaces route_code TEXT)
    
    standard_km REAL,
    actual_km REAL,
    purchase_price REAL,
    selling_price REAL,
    purchase_amount REAL,
    selling_amount REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (route_id) REFERENCES routes(id)
);

-- Indexes for daily_prices_v2
CREATE INDEX IF NOT EXISTS idx_daily_prices_v2_date ON daily_prices_v2(date);
CREATE INDEX IF NOT EXISTS idx_daily_prices_v2_route_id ON daily_prices_v2(route_id);
CREATE INDEX IF NOT EXISTS idx_daily_prices_v2_date_route ON daily_prices_v2(date, route_id);

-- ============================================================================
-- MIGRATION TRACKING TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,                          -- 'success', 'failed', 'partial'
    records_migrated INTEGER DEFAULT 0,
    error_message TEXT
);

