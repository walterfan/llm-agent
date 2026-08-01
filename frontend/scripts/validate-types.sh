#!/bin/bash
# Validate that TypeScript types are in sync with backend
# This prevents deployment of code with outdated types

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
GENERATED_FILE="src/types/api.generated.ts"
TEMP_FILE="$GENERATED_FILE.new"

echo "🔍 Validating type synchronization..."

# Check if backend is running
if ! curl -s -f "$BACKEND_URL/api/health" > /dev/null 2>&1; then
    echo "❌ Backend is not running at $BACKEND_URL"
    echo "💡 Start backend: make start-backend"
    exit 1
fi

# Check if generated types exist
if [ ! -f "$GENERATED_FILE" ]; then
    echo "❌ Generated types not found: $GENERATED_FILE"
    echo "💡 Generate types first: npm run generate-types"
    exit 1
fi

# Generate new types to temp file
echo "📡 Fetching current schema from backend..."
npx openapi-typescript "$BACKEND_URL/api/v1/openapi.json" \
    --output "$TEMP_FILE" \
    --export-type \
    > /dev/null 2>&1

# Compare with existing types (ignore comments and timestamps)
echo "🔍 Comparing with existing types..."
DIFF=$(diff \
    <(grep -v "^/\*\*\|^ \*\|This file was auto-generated" "$GENERATED_FILE" | sort) \
    <(grep -v "^/\*\*\|^ \*\|This file was auto-generated" "$TEMP_FILE" | sort) \
    || true)

# Clean up temp file
rm -f "$TEMP_FILE"

if [ -n "$DIFF" ]; then
    echo "❌ Types are out of sync with backend!"
    echo ""
    echo "📋 Differences found:"
    echo "$DIFF" | head -20
    echo ""
    echo "💡 To fix:"
    echo "   npm run generate-types"
    echo "   git add src/types/api.generated.ts"
    exit 1
fi

echo "✅ Types are in sync with backend"
exit 0
