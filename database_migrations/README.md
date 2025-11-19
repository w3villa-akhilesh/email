# Database Migrations

This directory contains database migration scripts to keep your database schema in sync with the application models.

## Current Migrations

### 1. Add app_name column to iats_user_sessions table

**File:** `add_app_name_column.sql` / `migrate_app_name_column.py`

**Purpose:** Fixes the error "Unknown column 'iats_user_sessions.app_name' in 'field list'"

**What it does:**
- Adds the missing `app_name` column to the `iats_user_sessions` table
- Creates an index for better query performance
- Sets all existing records to have `app_name = 'iats_sequential_flow'`
- Allows the application to properly filter sessions by application name

**How to run:**

**Option 1: Python script (Recommended)**
```bash
cd database_migrations
python migrate_app_name_column.py
```

**Option 2: SQL manually**
```sql
ALTER TABLE iats_user_sessions ADD COLUMN app_name VARCHAR(255) NULL;
CREATE INDEX idx_iats_user_sessions_app_name ON iats_user_sessions(app_name);
```

## Running Migrations

1. Ensure your `.env` file has the correct database credentials
2. Navigate to the `database_migrations` directory
3. Run the appropriate migration script
4. Verify the changes were applied successfully

## Adding New Migrations

When adding new migrations:
1. Create both SQL and Python versions
2. Update this README with migration details
3. Test the migration on a development database first
4. Include rollback instructions if possible
