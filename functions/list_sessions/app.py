import json
import os

import boto3
from boto3.dynamodb.conditions import Key

ddb = boto3.resource("dynamodb").Table(os.environ["MEMORY_TABLE"])
ACTOR_ID = os.environ["ACTOR_ID"]


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    status_filter = params.get("status")
    limit = min(int(params.get("limit", 50)), 100)

    if status_filter:
        resp = ddb.query(
            IndexName="by-status",
            KeyConditionExpression=Key("status").eq(status_filter),
            ScanIndexForward=False,
            Limit=limit,
        )
    else:
        resp = ddb.query(
            IndexName="by-date",
            KeyConditionExpression=Key("actor_id").eq(ACTOR_ID),
            ScanIndexForward=False,
            Limit=limit,
        )

    return {"statusCode": 200, "body": json.dumps(resp.get("Items", []), default=str)}
