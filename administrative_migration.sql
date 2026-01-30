-- ============================================================================
-- Administrative Module Migration Script
-- ============================================================================
-- Creates the documents table for Legal, Administrative/HR, and Tax documents
-- ============================================================================

BEGIN TRANSACTION;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Category: legal, administrative, tax
    category TEXT NOT NULL CHECK(category IN ('legal', 'administrative', 'tax')),
    
    -- Document type (e.g., 'contract', 'license', 'tax_return', 'employee_contract')
    document_type TEXT NOT NULL,
    
    -- Related entity (polymorphic relationship)
    related_entity_type TEXT,  -- e.g., 'vehicle', 'employee', 'company', NULL for general
    related_entity_id INTEGER,  -- ID of the related entity
    
    -- Document details
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,  -- Relative path to file (not blob)
    
    -- Dates
    issued_date DATE,
    expiry_date DATE,  -- Nullable
    
    -- Status
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'expired', 'archived')),
    
    -- Metadata
    description TEXT,  -- Optional description
    notes TEXT,  -- Optional notes
    
    -- Audit fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,  -- FK to accounts.id
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,  -- FK to accounts.id
    
    FOREIGN KEY (created_by) REFERENCES accounts(id),
    FOREIGN KEY (updated_by) REFERENCES accounts(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_related_entity ON documents(related_entity_type, related_entity_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_expiry_date ON documents(expiry_date);
CREATE INDEX IF NOT EXISTS idx_documents_issued_date ON documents(issued_date);
CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by);

-- Log migration
INSERT OR IGNORE INTO migration_log (migration_name, status, records_migrated)
VALUES ('administrative_migration', 'success', 0);

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

