# Capcan HIDS - Comprehensive Test Plan (March 2026)

## Executive Summary

**Target**: 50-70% coverage via 328 tests in 35+ files  
**Framework**: pytest + fixtures + mocking  
**Timeline**: 5 weeks in phases

---

## Critical Blockers (Fix First)

| Issue | Location | Fix | Time |
|-------|----------|-----|------|
| Function naming | validators.py:38 | Rename `validate_hmac()` → `validate_timestamp()` | 5 min |
| Missing SQL enums | config.py | Create 4 enum types (STATUS, ALERT_SEVERITY, ALERT_STATUS, CHANGE_STATUS) | 10 min |
| Syntax error | config.py:145 | Remove colon: `agent_count:` → `agent_count` | 5 min |
| Syntax error | config.py:206 | Remove trailing comma after timestamp field | 5 min |

---

## Database Schema (12 Tables)

### Active Tables (6) - Used by API
- **registered_clients**: Root table, all others reference via FK cascade
- **client_telemetry**: Time-series metrics, JSONB storage, status enum
- **client_alerts**: Security alerts, severity/status enums, acknowledged flags
- **client_events**: File/process events (unused by API currently)
- **client_changes**: Configuration changes, change_status enum (unused)
- **client_configs**: Client configuration storage, JSONB (unused)

### Inactive Tables (6) - Defined but not called
- server_details (syntax error), auth, user_permissions, client_organizations, notification_integrations (syntax error), server_audit_logs

---

## Test Files & Functions Overview

### Unit Tests (70 tests)

| File | Tests | Purpose |
|------|-------|---------|
| **test_validators.py** | 22 | HMAC validation, timestamp checks, edge cases |
| **test_response_utils.py** | 16 | Response formatting, pagination, errors |
| **test_signature_verification.py** | 15 | Cryptographic signature validation, timing |
| **test_timestamp_edge_cases.py** | 12 | Boundary conditions, format validation, clock skew |
| **test_enums.py** | 5 | Enum value validation (platform, severity, type, status) |

**Key Functions Tested**:
- `validate_timestamp(timestamp, max_age)` - Age/format validation
- `validate_ack_id(ack_id)` - Acknowledgment ID format
- `format_success_response(data)`, `format_error_response(error)` - Response wrapping
- `verify_hmac_signature(signature, expected)` - Timing-safe comparison
- Enum member validation and value constraints

---

### API Integration Tests (102 tests)

#### Client Endpoints (24 tests - test_client_endpoints.py)
- Registration: valid/invalid data, duplicate client IDs, metadata validation
- Heartbeat: status updates, missing fields, authentication
- Info retrieval: by ID, 404 handling, rate limiting
- Status updates: state transitions, validation

#### Alert Endpoints (28 tests - test_alert_endpoints.py)
- Submission: validation, duplicate IDs, metadata
- Bulk operations: batch processing, partial failures
- Acknowledgment: state transitions, timestamp tracking
- Retrieval: filtering, pagination, sorting

#### Telemetry Endpoints (20 tests - test_telemetry_endpoints.py)
- Submission: JSONB storage, validation, timestamps
- History retrieval: filtering by date range, limits
- Latest data: single point queries, missing data handling
- Statistics: aggregation, minimum data thresholds

#### Security Tests (30 tests - test_api_security.py)
- HMAC authentication: valid/invalid signatures across all endpoints
- Replay attack prevention: timestamp validation, future/past rejection
- Timing attack resistance: consistent verification time
- Data integrity: tampering detection, body verification
- Header validation: missing/partial headers, format checking

---

### Database Integration Tests (95 tests)

#### Schema Validation (15 tests - test_database_schema.py)
- Enum type creation (STATUS, ALERT_SEVERITY, ALERT_STATUS, CHANGE_STATUS)
- Table existence, column types, constraints
- Primary key enforcement, index creation

#### CRUD Operations by Table (70 tests)
- **test_registered_clients.py** (12): Insert, read, update, delete, cascade behavior
- **test_client_telemetry.py** (14): JSONB storage, status validation, time ranges
- **test_client_alerts.py** (14): Severity/status enums, filtering, acknowledgment
- **test_client_events.py** (8): Event type handling, payload storage
- **test_client_changes.py** (8): State transitions, applied_at tracking
- **test_client_configs.py** (6): Configuration updates, versioning

#### Constraints & Relationships (18 tests)
- **test_foreign_keys.py** (10): FK constraint enforcement, orphaned data prevention
- **test_cascade_deletes.py** (8): Delete propagation across related tables

---

### Web UI Integration Tests (34 tests)

| File | Tests | Purpose |
|------|-------|---------|
| test_dashboard_routes.py | 12 | Home page, stats summary, client counts |
| test_clients_routes.py | 8 | Client list, detail view, add/edit forms |
| test_settings_routes.py | 8 | Configuration UI, preferences, system settings |
| test_auth_routes.py | 6 | Login/register forms, session handling |

---

### End-to-End Tests (49 tests)

| File | Tests | Purpose |
|------|-------|---------|
| test_client_registration_flow.py | 12 | Full registration → heartbeat → telemetry flow |
| test_alert_lifecycle.py | 15 | Alert creation → acknowledgment → resolution |
| test_api_security_flows.py | 10 | Multi-step security validation scenarios |
| test_database_integration.py | 12 | Complete workflows with persistent data |

---

## Test Fixtures

### fixtures/security_fixtures.py
- `generate_hmac_signature(client_id, secret_key, data)` - Valid signatures
- `generate_invalid_hmac_signature(client_id, secret_key, data, type)` - Intentional errors
- `create_expired_timestamp()`, `create_future_timestamp()` - Boundary timestamps
- `create_security_test_matrix()` - Comprehensive test case matrix

### fixtures/client_fixtures.py
- `create_sample_client()` - Single test client
- `create_client_registration_payload()` - Registration data
- `create_client_heartbeat_payload()` - Heartbeat metrics
- `create_multiple_clients(count)` - Bulk test data

### fixtures/alert_fixtures.py
- `create_sample_alert()` - Single alert
- `create_multiple_alerts(count)` - Bulk alerts
- `create_critical_alert()`, `create_acknowledged_alert()` - Various states
- `create_bulk_alerts_payload()` - Batch format

### fixtures/telemetry_fixtures.py
- `create_sample_telemetry_data()` - Single data point
- `create_telemetry_time_series(client_id, hours)` - Time-series data
- `create_high_load_telemetry()`, `create_low_resource_telemetry()` - Scenarios
- `create_telemetry_statistics_data()` - Aggregation results

### fixtures/database_fixtures.py
- `@fixture db` - Database connection for tests
- `@fixture clean_db` - Clean state before each test (TRUNCATE CASCADE)
- `@fixture test_client` - Inserted test client row
- `@fixture test_alert`, `@fixture test_telemetry` - Related data
- `@fixture bulk_clients`, `@fixture bulk_alerts` - Volume testing

---

## Test Directory Structure
