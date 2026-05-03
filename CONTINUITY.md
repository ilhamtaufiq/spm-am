# Continuity Ledger - SIMSPAM Super App

## Goal (incl. success criteria):
- Enhance SPM Dashboard with better data integrity, performance, and features.
- Success: Data deduplicated, schema hardened (FKs, Indexes, Constraints), and SIMSPAM registration tracking implemented.
- Success: Village names standardized (UPPERCASE, NO SPACES).

## Constraints/Assumptions:
- Database: SQLite (`data/spm_am.db`).
- Tech: FastAPI + SQLAlchemy + Vanilla JS.
- Persona: Casual "gaul" Indonesian.

## Key decisions:
- Use `is_simspam` column (Integer 0/1) for simspam.id registration status.
- Standardize village names to `BABAKANKARET` format for consistent matching.
- Use a dedicated migration script (`deploy_migration.py`) for schema updates.

## State:
- **Done**:
    - Bulk update notes feature.
    - Database hardening (indexes, unique constraints, audit fields).
    - Restore/Recover data after migration glitch.
    - Fixed "Add Data" village dropdown API.
    - Added SIMSPAM column and toggle logic.
    - Standardized existing data to UPPERCASE_NOSPACES.
    - **Database Normalization**: Successfully transitioned to relational schema (Kecamatan, Desa, UnitSpam, Pengelola, Achievement).
    - **Migration**: 32 Kecamatan and 360 Units migrated and verified.
- **Now**:
    - Final validation of UI layout and column order with normalized data.
    - Verifying annual breakdown modal functionality.
- **Next**:
    - Final user verification of the entire flow.

## Open questions:
- None for now.

## Working set:
- `main.py`
- `models.py`
- `templates/index.html`
- `deploy_migration.py` (New deployment tool)
