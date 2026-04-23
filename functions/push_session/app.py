import json
import os
import time
from datetime import datetime, timezone

import boto3

agentcore = boto3.client("bedrock-agentcore")
ddb = boto3.resource("dynamodb").Table(os.environ["MEMORY_TABLE"])

MEMORY_ID = os.environ["MEMORY_ID"]
ACTOR_ID = os.environ["ACTOR_ID"]
MAX_CONTENT = 9000


def handler(event, context):
    body = json.loads(event.get("body", "{}"))
    content = body.get("content", "")[:MAX_CONTENT]
    session_id = body.get("session_id", f"session-{datetime.now().strftime('%m-%d-%y')}")
    tags = body.get("tags", {})
    status = tags.get("status", "unknown")

    if not content:
        return {"statusCode": 400, "body": json.dumps({"error": "content is required"})}

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build metadata for AgentCore
    metadata = {k: {"stringValue": v} for k, v in tags.items()}

    # Push to AgentCore Memory
    agentcore.create_event(
        memoryId=MEMORY_ID,
        actorId=ACTOR_ID,
        sessionId=session_id,
        eventTimestamp=timestamp,
        payload=[{"conversational": {"content": {"text": content}, "role": "ASSISTANT"}}],
        metadata=metadata,
    )

    # Index in DynamoDB
    ttl = int(time.time()) + (int(os.environ.get("EVENT_EXPIRY_DAYS", 365)) * 86400)
    ddb.put_item(
        Item={
            "actor_id": ACTOR_ID,
            "session_id": session_id,
            "created_at": now.isoformat(),
            "status": status,
            "tags": tags,
            "summary": content[:200],
            "ttl": ttl,
        }
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Session {session_id} saved", "session_id": session_id}),
    }
