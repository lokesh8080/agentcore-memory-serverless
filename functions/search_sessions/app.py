import json
import os

import boto3
from boto3.dynamodb.conditions import Key

agentcore = boto3.client("bedrock-agentcore")
ddb = boto3.resource("dynamodb").Table(os.environ["MEMORY_TABLE"])

MEMORY_ID = os.environ["MEMORY_ID"]
ACTOR_ID = os.environ["ACTOR_ID"]
NAMESPACE = os.environ["NAMESPACE"]


def handler(event, context):
    body = json.loads(event.get("body", "{}"))
    query = body.get("query", "")
    tags = body.get("tags", {})
    index_only = body.get("index_only", False)

    results = {"index_matches": [], "memory_matches": []}

    # Always query DynamoDB index first (fast, exact)
    if tags.get("status"):
        resp = ddb.query(
            IndexName="by-status",
            KeyConditionExpression=Key("status").eq(tags["status"]),
            ScanIndexForward=False,
            Limit=20,
        )
    else:
        resp = ddb.query(
            KeyConditionExpression=Key("actor_id").eq(ACTOR_ID),
            ScanIndexForward=False,
            Limit=20,
        )
    results["index_matches"] = resp.get("Items", [])

    # Semantic search via AgentCore (unless caller only wants the index)
    if not index_only and query:
        namespace = f"{NAMESPACE}/{ACTOR_ID}"
        search_criteria = {"searchQuery": query}
        if tags:
            search_criteria["metadataFilters"] = {k: {"stringValue": v} for k, v in tags.items()}

        mem_resp = agentcore.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=namespace,
            searchCriteria=search_criteria,
        )
        results["memory_matches"] = [
            {
                "content": r["content"]["text"],
                "score": str(r.get("score", "")),
                "created_at": r.get("createdAt", ""),
            }
            for r in mem_resp.get("memoryRecordSummaries", [])
        ]

    return {"statusCode": 200, "body": json.dumps(results, default=str)}
