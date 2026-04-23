#!/bin/bash
# Push session to AgentCore Memory via API Gateway
# Usage: echo "summary" | push-session.sh [session-id] [key=val,key2=val2]
#
# Requires: API_ENDPOINT environment variable (from CloudFormation output)

API_ENDPOINT="${API_ENDPOINT:?Set API_ENDPOINT from CloudFormation output}"

SESSION_ID="${1:-session-$(date +%m-%d-%y)}"
[[ -n "$1" && ! "$1" =~ [0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] && SESSION_ID="${1}-$(date +%m-%d-%y)"

CONTENT=$(cat)
[ -z "$CONTENT" ] && echo "Error: Pipe content to this script." >&2 && exit 1

# Parse comma-separated tags into JSON object
TAGS="{}"
if [ -n "$2" ]; then
  TAGS=$(python3 -c "
import json, sys
pairs = '$2'.split(',')
print(json.dumps({p.split('=')[0]: p.split('=')[1] for p in pairs}))
")
fi

PAYLOAD=$(python3 -c "
import json, sys
content = sys.stdin.read()[:9000]
print(json.dumps({'session_id': '$SESSION_ID', 'content': content, 'tags': $TAGS}))
" <<< "$CONTENT")

curl -s -X POST "$API_ENDPOINT/sessions" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --aws-sigv4 "aws:amz:${AWS_REGION:-us-east-1}:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" 2>&1

echo "" >&2
echo "✅ Session pushed: $SESSION_ID" >&2
