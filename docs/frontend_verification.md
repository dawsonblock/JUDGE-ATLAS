# Frontend Verification Status (HISTORICAL)

> ⚠️ **This is a historical artifact.** Committed proof logs reflect the state at the time of commit.
> For current verification status, run `./scripts/verify_frontend.sh` from a clean checkout.

**Date:** 2025-04-28

## Environment

- Node version required: 20 (`.nvmrc` = `20`, `Dockerfile` uses `node:20-slim`)
- Node available in this environment: v24.14.0 (system)
- `npm` available: No (`npm: command not found` in this environment)

## Verification Steps

The verification script is `scripts/verify_frontend.sh` which runs:

1. `node --version` — Node 20+ check
2. `npm ci` — clean install from `package-lock.json`
3. `npm run lint` — ESLint via `next lint`
4. `npm run typecheck` — `tsc --noEmit`
5. `npm run build` — Next.js production build

## Known Gap

`npm` is not available in the current local runtime (`codex-primary-runtime`).
Frontend verification **cannot be reproduced** in this environment.

Verified state from Docker Dockerfile (`frontend/Dockerfile`):
- Uses `node:20-slim` base image
- Runs `npm ci` then `npm run build`
- This is the canonical verification path

## To Verify Locally

```bash
nvm use 20   # or: node --version must show v20.x
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

Or run the Docker build:

```bash
docker compose build frontend --no-cache
```

## What Was Checked (Static Review)

| Check | Result |
|---|---|
| `.nvmrc` specifies Node 20 | PASS |
| `Dockerfile` uses `node:20-slim` | PASS |
| `package.json` has `lint` script | PASS |
| `package.json` has `typecheck` script | PASS |
| `package.json` has `build` script | PASS |
| `tsconfig.json` present and valid | PASS |
| `.eslintrc.json` present | PASS |
| No banned privacy terms in TSX components (static grep) | PASS (see Phase 9) |
| `SourcePanel.tsx` contains source-scope disclaimer | PASS (see Phase 9) |
| Admin review page uses `X-JTA-Admin-Token` header | PASS |
| Map component filters `repeat_offender_indicator` by name | PASS |
