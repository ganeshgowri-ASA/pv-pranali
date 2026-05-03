# Infra — Account Setup Guide

## Purpose
Configure credentials and API keys for all external services used in the
Pranali Engineering workflow.

> **Note**: All agents default to `dry_run=True` until credentials are
> provisioned and explicitly enabled.

## Services

### Component Distributors

| Service | Purpose | Auth Method | Env Var | Status |
|---------|---------|-------------|---------|--------|
| Mouser Electronics | Component search + pricing | API Key | `MOUSER_API_KEY` | ☐ |
| DigiKey | Component search + pricing | OAuth2 | `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` | ☐ |
| Element14 India | Component search + pricing | API Key | `ELEMENT14_API_KEY` | ☐ |
| Rajguru Electronics | IN-local pricing | Web/manual | — | ☐ |
| Mehta Associates | IN-local pricing | Web/manual | — | ☐ |
| Kaizen Components | IN-local pricing | Web/manual | — | ☐ |

### Automation & Observability

| Service | Purpose | Auth Method | Env Var | Status |
|---------|---------|-------------|---------|--------|
| Langfuse | LLM observability + prompt tracing | API Key | `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` | ☐ |
| Skyvern | Browser automation (RIL portal) | API Key | `SKYVERN_API_KEY` | ☐ |
| Unipile | Email/calendar integration | API Key | `UNIPILE_API_KEY` | ☐ |

### Customer Portal

| Service | Purpose | Auth Method | Env Var | Status |
|---------|---------|-------------|---------|--------|
| RIL Supplier Portal | Submission of proposals, compliance docs | SSO / Login | `RIL_PORTAL_USER`, `RIL_PORTAL_PASS` | ☐ |

## Setup Steps

1. Copy `.env.example` to `.env` (never commit `.env`).
2. Fill in each `Env Var` above in `.env`.
3. For DigiKey: create app at developer.digikey.com → OAuth2 Client Credentials.
4. For Mouser: register at mouser.com/api → generate API key.
5. For Element14: register at element14.com/community/docs/DOC-94005.
6. For Langfuse: create account at langfuse.com → Settings → API Keys.
7. For Skyvern: contact skyvern.com for API access.
8. For Unipile: create account at unipile.com → API Settings.
9. Test each connection: `python infra/test_connections.py --dry-run`.

## Security Notes
- `.env` is gitignored.
- Rotate API keys quarterly.
- Do not log credentials to Langfuse traces.
- RIL portal credentials: use a service account, not personal login.

## dry_run Behavior
When `dry_run=True` (default):
- All API calls return mock responses.
- No orders are placed.
- No documents are submitted to RIL portal.
- Langfuse traces are written to local log file only.
