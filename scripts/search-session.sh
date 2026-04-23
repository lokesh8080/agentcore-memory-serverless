#!/bin/bash
# Search sessions via API Gateway
# Usage:
#   search-session.sh                          # list all sessions
#   search-session.sh "query"                  # semantic search
#   search-session.sh "query" "key=val"        # search with metadata filter
#   search-session.sh --status in-progress     # filter by status

API_ENDPOINT="${API_ENDPOINT:?Set API_ENDPOINT from CloudFormation output}"
REGION="${AWS_REGION:-us-east-1}"

# Status-only filter
if [ "$1" = "--status" ]; then
  curl -s "$API_ENDPOINT/sessions?status=$2" \
    --aws-sigv4 "aws:amz:$REGION:execute-api" \
    --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" | python3 -m json.tool
  exit 0
fi

# No args: list all sessions
if [ -z "$1" ]; then
  echo "📋 Recent sessions:" >&2
  curl -s "$API_ENDPOINT/sessions" \
    --aws-sigv4 "aws:amz:$REGION:execute-api" \
    --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" | python3 -m json.tool
  exit 0
fi

# Semantic search with optional tags
TAGS="{}"
if [ -n "$2" ]; then
  TAGS=$(python3 -c "
import json
pairs = '$2'.split(',')
print(json.dumps({p.split('=')[0]: p.split('=')[1] for p in pairs}))
")
fi

PAYLOAD=$(python3 -c "
import json
print(json.dumps({'query': '$1', 'tags': $TAGS}))
")

echo "🔍 Searching..." >&2
curl -s -X POST "$API_ENDPOINT/sessions/search" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --aws-sigv4 "aws:amz:$REGION:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" | python3 -m json.tool
