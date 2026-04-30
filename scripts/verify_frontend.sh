#!/bin/bash
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
ARTIFACTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/artifacts/proof/frontend"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${ARTIFACTS_DIR}/${TIMESTAMP}.log"

mkdir -p "${ARTIFACTS_DIR}"

# Route all output to stdout AND the log file
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== Frontend Verification — ${TIMESTAMP} ==="

cd "${FRONTEND_DIR}"

# ---------------------------------------------------------------------------
# 1. Require Node 20 exactly — fail if not
# ---------------------------------------------------------------------------
echo ""
echo "1. Checking Node version ..."
NODE_VERSION="$(node --version 2>/dev/null || echo "not-found")"
if [[ "${NODE_VERSION}" != v20.* ]]; then
    echo "ERROR: Node 20 is required. Found: ${NODE_VERSION}"
    echo "Install Node 20 (e.g. via nvm: nvm install 20 && nvm use 20) and re-run."
    exit 1
fi
echo "   Node: ${NODE_VERSION} — OK"
echo "   npm:  $(npm --version)"

# ---------------------------------------------------------------------------
# 2–5. Install, lint, typecheck, build
# ---------------------------------------------------------------------------
echo ""
echo "2. Clean install (npm ci) ..."
npm ci

echo ""
echo "3. Lint ..."
npm run lint

echo ""
echo "4. Typecheck ..."
npm run typecheck

echo ""
echo "5. Build ..."
npm run build

echo ""
echo "=== Frontend verification PASSED ==="
echo "Log: ${LOG_FILE}"
