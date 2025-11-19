# Rexnord Agent API

This document describes the Rexnord agent FastAPI app exposed by `rexnord_main.py`: its endpoint, how to run it locally, required headers, example requests, and expected responses.

## Overview

- Endpoint: `/invoke-rexnord-agent`
- Purpose: Routes user queries to Rexnord sub‑agents (dealer, products, product details, FAQ, contact) and returns the agent’s final response.
- Input Model: `RexnordTriageAgentRequest` with `query`, `query_id`, and `profile_info`.
- Core Flow:
  - Validates `origin` header against an allowlist.
  - Validates presence of `profile_info` (must include `company_id`).
  - Builds `session_id` from `query_id`.
  - Invokes `initiate_rexnord_agent(...)` and returns `{ response, event_id }`.

## Run Locally

Preferred (explicit app, recommended for development):

- `uvicorn rexnord_main:app --host 0.0.0.0 --port 8080`

Notes:
- The module’s `__main__` block runs `uvicorn.run("main:app", port=8081)`, which targets the root `main.py` app. To run only the Rexnord app, use the uvicorn command above.
- The top‑level project `README.md` references port `8080`. For consistency, the examples below use port `8080` with `uvicorn rexnord_main:app`.

## Required Headers

- `Content-Type: application/json`
- `origin: https://crm.kivo.ai/` (or `https://staging-crm.kivo.ai/`)
- `X-Request-Mode: crm`

The Rexnord endpoint enforces an origin allowlist. For local testing, set `origin` to one of the allowed production/staging origins listed above.

## Request Body

`profile_info` must include `company_id` for downstream credential loading and tracking.

```json
{
  "query": "what products you have?",
  "query_id": "rexnord@gmail.com",
  "profile_info": {
    "name": "John Doe",
    "number": "+91-9876543210",
    "company_id": "1"
  }
}
```

## cURL Examples

Local (using uvicorn on port 8080):

```bash
curl --location 'http://127.0.0.1:8080/invoke-rexnord-agent' \
  --header 'Content-Type: application/json' \
  --header 'origin: https://crm.kivo.ai/' \
  --header 'X-Request-Mode: crm' \
  --data-raw '{
    "query": "what products you have?",
    "query_id": "rexnord@gmail.com",
    "profile_info": {
      "name": "John Doe",
      "number": "+91-9876543210",
      "company_id": "1"
    }
  }'
```

Alternate local port (if you intentionally run on 8081):

```bash
uvicorn rexnord_main:app --host 0.0.0.0 --port 8081

curl --location 'http://127.0.0.1:8081/invoke-rexnord-agent' \
  --header 'Content-Type: application/json' \
  --header 'origin: https://crm.kivo.ai/' \
  --header 'X-Request-Mode: crm' \
  --data-raw '{
    "query": "what products you have?",
    "query_id": "rexnord@gmail.com",
    "profile_info": {
      "name": "John Doe",
      "number": "+91-9876543210",
      "company_id": "1"
    }
  }'
```

## Response Shape

On success:

```json
{
  "status": "success",
  "type": "final_response",
  "message": "Rexnord Agent invoked",
  "query": "what products you have?",
  "response": "... agent reply ...",
  "session_id": "session_rexnord@gmail.com",
  "event_id": "<event-uuid>"
}
```

On access error (invalid origin or missing profile):

```json
{
  "status": "error",
  "message": "Provided origin does not have access. Please contact the administrator."
}
```

or

```json
{
  "status": "error",
  "message": "You do not have access. Please contact the administrator."
}
```

## Implementation Pointers

- File: `rexnord_main.py`
- Endpoint: `@app.post("/invoke-rexnord-agent")`
- Allowed origins (normalized compare): `https://crm.kivo.ai/`, `https://staging-crm.kivo.ai/`
- Invoker: `rexnord.helpers.rexnord_triage_agent.initiate_rexnord_agent`
- Error notifications: `app.services.email_notifier.send_exception_email`

## Prerequisites

- Environment configured as per the project `README.md` (`.env`, DB, Redis, and LLM credentials as needed by sub‑agents).
- `profile_info.company_id` must map to valid credentials in your environment.
- REXNORD_INVENTORY_TOKEN= ''
- REXNORD_INVENTORY_BASE_URL = ''
- REXNORD_STORE_ID = ''

