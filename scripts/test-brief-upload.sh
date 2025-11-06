#!/bin/bash
# Smoke test script for brief upload functionality
# Tests both API routes and verifies idempotency

set -e

API_URL="${API_URL:-http://localhost:8080}"
TEST_FILE="${TEST_FILE:-/tmp/test-brief.txt}"

# Create a test file if it doesn't exist
if [ ! -f "$TEST_FILE" ]; then
    echo "Creating test file: $TEST_FILE"
    echo "Test brief content" > "$TEST_FILE"
fi

echo "Testing brief upload endpoints..."
echo "API URL: $API_URL"
echo ""

# Test 1: POST /briefs/upload
echo "Test 1: POST /briefs/upload"
RESPONSE1=$(curl -s -X POST "$API_URL/briefs/upload" \
    -F "file=@$TEST_FILE" \
    -F "locale=en" \
    -F "name=Test User" \
    -F "company=Test Company" \
    -F "phone=+1234567890" \
    -F "email=test@example.com" \
    -F "message=Test message")

echo "Response: $RESPONSE1"
REQUEST_ID1=$(echo "$RESPONSE1" | grep -o '"request_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$REQUEST_ID1" ]; then
    echo "ERROR: No request_id in response"
    exit 1
fi

echo "Request ID: $REQUEST_ID1"
echo ""

# Test 2: POST /api/briefs/upload (should work the same)
echo "Test 2: POST /api/briefs/upload"
RESPONSE2=$(curl -s -X POST "$API_URL/api/briefs/upload" \
    -F "file=@$TEST_FILE" \
    -F "locale=en" \
    -F "name=Test User 2" \
    -F "company=Test Company 2" \
    -F "phone=+1234567891" \
    -F "email=test2@example.com" \
    -F "message=Test message 2")

echo "Response: $RESPONSE2"
REQUEST_ID2=$(echo "$RESPONSE2" | grep -o '"request_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$REQUEST_ID2" ]; then
    echo "ERROR: No request_id in response"
    exit 1
fi

echo "Request ID: $REQUEST_ID2"
echo ""

# Test 3: Duplicate submission (should return dedup:true)
echo "Test 3: Duplicate submission (idempotency test)"
RESPONSE3=$(curl -s -X POST "$API_URL/briefs/upload" \
    -F "file=@$TEST_FILE" \
    -F "locale=en" \
    -F "name=Test User" \
    -F "company=Test Company" \
    -F "phone=+1234567890" \
    -F "email=test@example.com" \
    -F "message=Test message")

echo "Response: $RESPONSE3"
REQUEST_ID3=$(echo "$RESPONSE3" | grep -o '"request_id":"[^"]*' | cut -d'"' -f4)
DEDUP=$(echo "$RESPONSE3" | grep -o '"dedup":true' || echo "")

if [ "$REQUEST_ID3" != "$REQUEST_ID1" ]; then
    echo "ERROR: Duplicate request returned different request_id"
    echo "Expected: $REQUEST_ID1"
    echo "Got: $REQUEST_ID3"
    exit 1
fi

if [ -z "$DEDUP" ]; then
    echo "ERROR: Duplicate request should have dedup:true"
    exit 1
fi

echo "Request ID (should match first): $REQUEST_ID3"
echo "Dedup flag: $DEDUP"
echo ""

echo "✅ All tests passed!"
echo ""
echo "Summary:"
echo "  - /briefs/upload: ✅ Working"
echo "  - /api/briefs/upload: ✅ Working"
echo "  - Idempotency: ✅ Working (dedup:true on duplicate)"

