# Product Telemetry & Funnel Analytics

## Overview

This document describes the product telemetry system for WinningCV, enabling measurement of user journeys and identification of friction points before commercialization.

## Pre-existing State

Before this implementation:
- **Analytics Tables**: None. No existing product analytics or event tracking in the database.
- **Auth Model**: External auth service providing `UserInfo` with `auth_user_id`, `email`, `display_name`, etc.
- **User Identity**: Authenticated users identified by `auth_user_id` and `email`. Anonymous sessions not supported.
- **Frontend**: React + Vite SPA with centralized `fetchAPI` wrapper in `services/api.js`.
- **Backend**: FastAPI with routers at `/api/v1/*`. Routes for CV, jobs, profile, auth already exist.

## Core Funnel Steps

The following funnel steps are instrumented:

| Step | Event Name | Description |
|------|------------|-------------|
| 1 | `session_start` | User logs in or starts authenticated session |
| 2 | `cv_upload` | User uploads a CV (new or to library) |
| 3 | `preferences_configure` | User saves job search preferences |
| 4 | `job_search_start` | User initiates a job search |
| 5 | `job_search_complete` | Job search finishes with results |
| 6 | `jobs_view` | User views matched jobs list |
| 7 | `job_details_open` | User clicks to view job details/link |
| 8 | `cv_generate_start` | User starts CV generation |
| 9 | `cv_generate_complete` | CV generation finishes successfully |
| 10 | `cv_preview` | User views generated CV preview |
| 11 | `cv_refine` | User refines/edits generated CV |
| 12 | `cv_download` | User downloads generated CV |
| 13 | `cv_save_library` | User saves generated CV to library |
| 14 | `application_status_update` | User updates job application status |

### Friction/Error Events

| Event Name | Description |
|------------|-------------|
| `search_empty_results` | Job search returned no matches |
| `cv_generation_failed` | CV generation failed |
| `validation_error` | Form validation error occurred |
| `api_error` | API request failed |

## Implementation

### Database Schema

Added migration: `init-db/05-product-telemetry.sql`

```sql
CREATE TABLE product_events (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(64),
    event_name VARCHAR(100) NOT NULL,
    funnel_step INTEGER,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    path VARCHAR(500),
    referrer VARCHAR(500),
    client_timestamp TIMESTAMP WITH TIME ZONE,
    server_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

Indexes:
- `idx_events_user_id` - Filter by user
- `idx_events_session_id` - Filter by session
- `idx_events_name` - Filter by event type
- `idx_events_funnel_step` - Funnel analysis
- `idx_events_server_timestamp` - Time-based queries

### Backend API

Route: `/api/v1/telemetry`

- `POST /api/v1/telemetry/events` - Record single or batch events
- `GET /api/v1/telemetry/analytics/funnel` - Funnel drop-off analysis (admin)
- `GET /api/v1/telemetry/analytics/summary` - Activity summary (admin)

Events are recorded asynchronously; failures are logged but never break user flow.

### Frontend Client

Module: `frontend/src/services/telemetry.js`

```javascript
import { track, trackFunnel, trackError } from './services/telemetry'

// Track funnel step
trackFunnel('cv_upload', { cv_id: 'xxx' })

// Track custom event
track('cv_download', { format: 'pdf', cv_id: 'xxx' })

// Track error
trackError('api_error', { endpoint: '/jobs', status: 500 })
```

The client:
- Batches events (up to 10, or 5s interval)
- Silently handles failures
- Auto-includes path, referrer, timestamp
- Generates session ID per browser session

### Admin Dashboard

Route: `/api/v1/telemetry/analytics/dashboard`

Provides:
- Active users/sessions over configurable period
- Funnel counts and drop-off rates
- Top events by volume
- Error events breakdown
- Generated CVs vs downloaded ratio

## Files Changed

### New Files
- `docs/product-telemetry.md` - This document
- `init-db/05-product-telemetry.sql` - Database migration
- `api/routes/telemetry.py` - Backend API routes
- `api/schemas/telemetry.py` - Pydantic schemas
- `frontend/src/services/telemetry.js` - Frontend telemetry client
- `tests/test_telemetry.py` - Backend tests

### Modified Files
- `api/routes/__init__.py` - Export telemetry router
- `api/main.py` - Include telemetry router
- `frontend/src/context/AuthContext.jsx` - Track session_start
- `frontend/src/pages/GenerateCV.jsx` - Track CV generation funnel
- `frontend/src/pages/Dashboard.jsx` - Track jobs viewing
- `frontend/src/services/api.js` - Track API errors

## Testing

Run tests:
```bash
pytest tests/test_telemetry.py -v
```

## Future Considerations

- Add retention policy for old events (cleanup after 90 days)
- Consider dedicated analytics DB if volume grows
- Potential integration with Segment/Amplitude later
- A/B testing infrastructure
