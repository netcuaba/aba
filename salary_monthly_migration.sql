-- ============================================================================
-- Salary Monthly Migration Script
-- ============================================================================
-- Creates the salary_monthly table to store monthly salary snapshots
-- ============================================================================

BEGIN TRANSACTION;

-- Create salary_monthly table
CREATE TABLE IF NOT EXISTS salary_monthly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
    year INTEGER NOT NULL,
    bao_hiem_xh INTEGER DEFAULT 0,
    rua_xe INTEGER DEFAULT 0,
    tien_trach_nhiem INTEGER DEFAULT 0,
    ung_luong INTEGER DEFAULT 0,
    sua_xe INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    UNIQUE(employee_id, month, year)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_salary_monthly_employee_month_year ON salary_monthly(employee_id, month, year);

COMMIT;
