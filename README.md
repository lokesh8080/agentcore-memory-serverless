# Serverless AI Session Memory with Amazon Bedrock AgentCore

Persistent session memory for AI coding assistants, deployed as serverless infrastructure on AWS.

## Architecture

```
CLI / AI Assistant
    │
    ├── POST /sessions          → Push Lambda → AgentCore Memory + DynamoDB Index
    ├── POST /sessions/search   → Search Lambda → DynamoDB + AgentCore Semantic Search
    └── GET  /sessions          → List Lambda → DynamoDB Index
                                      │
                              ┌───────┴────────┐
                              │   DynamoDB      │  Fast index lookups
                              │   (session      │  (by date, status, tags)
                              │    index)        │
                              └────────────────┘
                              ┌────────────────┐
                              │  AgentCore     │  Semantic fact extraction
                              │  Memory        │  + session summaries
                              └────────────────┘
```

## Deploy

```bash
# Clone and deploy
git clone https://github.com/lokesh8080/agentcore-memory-serverless.git && cd agentcore-memory-serverless && sam build && sam deploy --guided

# Get the API endpoint
export API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ai-session-memory \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)
```

## Usage

```bash
# Push a session
echo "Migrated Lambda constructs to CDK v2. Fixed BundlingOptions breaking change." | \
  ./scripts/push-session.sh "cdk-migration" "topic=cdk,status=in-progress"

# Search past work
./scripts/search-session.sh "CDK v2 breaking change"

# Filter by status
./scripts/search-session.sh --status in-progress

# List all sessions
./scripts/search-session.sh
```

## Clean Up

```bash
aws cloudformation delete-stack --stack-name ai-session-memory --region us-east-1
```

Note: The DynamoDB table has `DeletionPolicy: Retain` — delete it manually if you want to remove all data.
