# Give your AI coding assistant persistent memory with Amazon Bedrock AgentCore

AI coding assistants are powerful in the moment — but the moment you close the terminal, the context is gone. The debugging session you spent an hour on, the architecture decisions you made, the half-finished migration — all of it disappears when the session ends.

In this post, you learn how to deploy a serverless solution that gives your AI coding assistant long-term memory using [Amazon Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html). You push session summaries when you pause work, and search them with natural language when you resume — across days, projects, and machines.

## Overview

When you work with an AI coding assistant on a complex task — debugging a production issue, designing a multi-region architecture, migrating a service between frameworks — the conversation builds up valuable context: what you tried, what worked, what you decided, and what's left to do.

Today, that context lives only in the current session. If you close the terminal and come back tomorrow, you start from scratch. You re-explain the problem, re-describe the architecture, and lose the thread of decisions you already made.

This solution solves that problem with three components:

- **Amazon Bedrock AgentCore Memory** — Stores your session content and automatically extracts semantic facts and generates summaries using built-in AI strategies
- **Amazon DynamoDB** — Provides a fast, queryable index of all your sessions with filtering by status, date, and custom tags
- **Amazon API Gateway and AWS Lambda** — Exposes push, search, and list operations as API endpoints that any CLI tool can call

The following diagram shows how these components work together.

`[PLACEHOLDER: Architecture diagram — show CLI → API Gateway → Lambda → AgentCore Memory + DynamoDB. Use AWS Architecture Icons. Include the two memory strategies (semantic_facts, session_summaries) as labeled components inside the AgentCore Memory box.]`

## How it works

The workflow has two phases: pushing context when you pause, and searching for it when you resume.

**Pushing a session:**

1. You finish a work session and pipe a summary to the push script.
2. The script calls the API Gateway endpoint, which invokes a Lambda function.
3. The Lambda function sends the content to AgentCore Memory using the `CreateEvent` API and writes an index entry to DynamoDB.
4. AgentCore Memory asynchronously extracts semantic facts (individual decisions, findings, commands) and generates a session summary.

**Searching for context:**

1. You start a new session and call the search script with a natural language query.
2. The Lambda function queries DynamoDB first for fast, structured results (by status, date, tags).
3. It then calls AgentCore Memory's `RetrieveMemoryRecords` API for semantic search across extracted facts.
4. Both result sets are returned, giving you exact index matches and semantically relevant facts.

`[PLACEHOLDER: Sequence diagram or flow diagram showing the push and search flows side by side]`

## Prerequisites

To follow along with this post, you need the following:

- An [AWS account](https://aws.amazon.com/free/)
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) or the ability to run `aws cloudformation deploy` with the `AWS::Serverless` transform
- IAM permissions for AWS Lambda, Amazon API Gateway, Amazon DynamoDB, and Amazon Bedrock AgentCore
- Python 3 (used in the CLI helper scripts for JSON formatting)
- An AI coding assistant CLI tool (the solution works with any tool that can run shell commands)

## Deploy the solution

The entire solution deploys as a single AWS CloudFormation template using the AWS Serverless Application Model (SAM) transform.

### Step 1: Get the template

Clone or download the CloudFormation template:

```bash
git clone https://github.com/lokesh8080/agentcore-memory-serverless.git
cd agentcore-memory-serverless
```

The template creates the following resources:

| Resource | Type | Purpose |
|----------|------|---------|
| AgentCore Memory | `AWS::Bedrock::Memory` | Stores session content with semantic extraction and summarization |
| Session index table | `AWS::DynamoDB::Table` | Fast lookups by actor, date, and status with auto-expiry (TTL) |
| Push function | `AWS::Serverless::Function` | Receives session content, writes to AgentCore Memory and DynamoDB |
| Search function | `AWS::Serverless::Function` | Queries DynamoDB index and AgentCore semantic search |
| List function | `AWS::Serverless::Function` | Returns all sessions from DynamoDB, filterable by status |
| HTTP API | `AWS::Serverless::HttpApi` | API Gateway with IAM authentication |

### Step 2: Deploy the stack

```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name ai-session-memory \
  --parameter-overrides ActorId=YOUR_ALIAS \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --region us-east-1
```

Replace `YOUR_ALIAS` with your identifier. This value is used as the actor ID in AgentCore Memory and the partition key in DynamoDB.

### Step 3: Get the API endpoint

```bash
export API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name ai-session-memory \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text \
  --region us-east-1)

echo $API_ENDPOINT
```

### Step 4: Verify the deployment

Wait approximately 60 seconds for AgentCore Memory strategies to become active, then push a test session:

```bash
echo "Testing memory integration. Deployed the serverless session memory stack." | \
  ./scripts/push-session.sh "setup-test" "type=test,status=resolved"
```

Wait 30 seconds for semantic extraction, then search:

```bash
./scripts/search-session.sh "memory integration test"
```

You should see both DynamoDB index matches and AgentCore semantic matches in the response.

`[PLACEHOLDER: GIF — Terminal recording showing the push command, waiting, then the search command with results. Use asciinema or vhs to record. ~15 seconds.]`

## Use the solution

The solution includes two shell scripts that call the API endpoints. These scripts are thin wrappers — all logic runs in Lambda.

### Push a session

When you're done working, summarize what you did and push it:

```bash
echo "Migrated Lambda constructs from CDK v1 to v2. Fixed breaking change: \
BundlingOptions.image now requires DockerImage.fromRegistry() instead of \
Runtime.bundlingImage. All 47 unit tests passing. Remaining: DynamoDB table \
constructs and IAM policy statements." | \
  ./scripts/push-session.sh "cdk-migration" "topic=cdk-v2,status=in-progress"
```

The script accepts two optional arguments:

- **Session ID** — A human-readable name. The script auto-appends the date (for example, `cdk-migration` becomes `cdk-migration-03-23-26`).
- **Tags** — Comma-separated `key=value` pairs for structured filtering later.

### Search past sessions

Search with natural language:

```bash
./scripts/search-session.sh "CDK v2 BundlingOptions breaking change"
```

Or filter by metadata tags for more reliable results:

```bash
./scripts/search-session.sh "migration progress" "topic=cdk-v2"
```

Or filter by status to find unfinished work:

```bash
./scripts/search-session.sh --status in-progress
```

Or list all sessions:

```bash
./scripts/search-session.sh
```

### Browse the session index

When you work locally with a file like `memory-index.md`, you can quickly scan all your sessions — dates, tags, and summaries at a glance. The DynamoDB session index serves the same purpose, but serverless and queryable.

Every time you push a session, the Lambda function writes an index entry to DynamoDB with the session ID, timestamp, tags, status, and a 200-character summary. The List endpoint lets you browse this index the same way you'd scan a local file — but with filtering built in.

```bash
# List all sessions (equivalent to cat memory-index.md)
./scripts/search-session.sh

# Filter by status
./scripts/search-session.sh --status in-progress

# The API returns structured data: session ID, date, tags, and summary
# Example response:
# [
#   {
#     "session_id": "cdk-migration-03-23-26",
#     "created_at": "2026-03-23T14:30:00Z",
#     "status": "in-progress",
#     "tags": {"topic": "cdk-v2", "type": "development"},
#     "summary": "Migrated Lambda constructs from CDK v1 to v2. Fixed breaking change: BundlingOptions.image..."
#   },
#   ...
# ]
```

This gives you the quick-scan capability of a local index file, with the added benefit of filtering by status or date range — and it's accessible from any machine, not just the one where you saved the file.

`[PLACEHOLDER: GIF — Terminal recording showing a realistic workflow: push a session about a debugging task, then in a "new session" search for it and get results back. ~20 seconds.]`

### Use with your AI coding assistant

If your AI coding assistant can run shell commands, you can interact with memory using natural language. For example:

> *"Save this session to memory with session ID 'payments-api-debug' and tags topic=payments, status=in-progress"*

To resume later:

> *"Search my session memory for the payments API debugging work I was doing"*

Then:

> *"Use those results as context and let's continue where I left off"*

## Write effective summaries

The quality of your search results depends on what you put into the summary. AgentCore Memory's semantic extraction pulls out specific factual statements — not abstract concepts.

**Effective summary example:**

```
Migrated payments-service from CDK v1 to v2. Completed Lambda construct
migration using aws-cdk-lib. Fixed breaking change: BundlingOptions.image
now requires DockerImage.fromRegistry() instead of Runtime.bundlingImage.
Remaining: DynamoDB table constructs and IAM policy statements.
Used cdk diff to verify no resource replacements. All 47 unit tests passing.
```

This produces searchable facts like:
- *"Fixed CDK v2 breaking change: BundlingOptions.image requires DockerImage.fromRegistry()"*
- *"Used cdk diff to verify no resource replacements"*

**Ineffective summary example:**

```
Worked on the CDK migration. Made progress. Will continue tomorrow.
```

This produces almost nothing useful to search later.

**Summary template:**

```
What I was doing: [project/task name and goal]
What I used: [specific tools, services, APIs]
What I decided/found: [key decisions, root causes, solutions]
What's left: [next steps, blockers, open questions]
```

## Use consistent metadata tags

Consistent tags make structured filtering reliable across sessions:

| Tag | Example values | Purpose |
|-----|---------------|---------|
| `topic` | `cdk-migration`, `multi-region`, `cicd-pipeline` | What you're working on |
| `service` | `lambda`, `ecs`, `dynamodb` | Primary AWS service involved |
| `status` | `in-progress`, `blocked`, `resolved`, `paused` | Current state |
| `project` | `payments-v2`, `data-platform` | Project name |
| `type` | `debugging`, `design`, `development`, `research` | Type of work |

AgentCore Memory supports up to 15 metadata keys per event.

## Understand the search behavior

The search endpoint uses a two-tier approach:

1. **DynamoDB query (fast, exact)** — Returns index entries matching your actor ID, optionally filtered by status. Results include session ID, tags, date, and a 200-character summary.
2. **AgentCore semantic search (natural language)** — Searches across extracted facts using vector similarity. Returns ranked results with relevance scores.

Semantic search works well for specific technical terms:

```bash
# These return good results
./scripts/search-session.sh "CDK v2 BundlingOptions breaking change"
./scripts/search-session.sh "connection pool 503 error"
```

Semantic search works poorly for vague or conceptual queries:

```bash
# These return poor results
./scripts/search-session.sh "what was I working on last week"
./scripts/search-session.sh "that project I was doing"
```

For vague queries, use metadata filters instead:

```bash
./scripts/search-session.sh "remaining work" "status=in-progress"
./scripts/search-session.sh "error fix" "topic=cdk-migration"
```

## Clean up

To remove all resources created by this solution:

```bash
aws cloudformation delete-stack --stack-name ai-session-memory --region us-east-1
```

The DynamoDB table has a `DeletionPolicy` of `Retain` to prevent accidental data loss. To delete it manually:

```bash
aws dynamodb delete-table \
  --table-name ai-session-memory-session-index \
  --region us-east-1
```

## Conclusion

In this post, you deployed a serverless solution that gives your AI coding assistant persistent memory across sessions. Using Amazon Bedrock AgentCore Memory for semantic fact extraction, Amazon DynamoDB for fast structured lookups, and Amazon API Gateway with AWS Lambda for the API layer, you can now push session context when you pause work and search for it with natural language when you resume.

The solution works with any AI coding assistant that can run shell commands, requires no local dependencies beyond the AWS CLI, and costs only for what you use with pay-per-request DynamoDB and Lambda pricing.

To get started, deploy the CloudFormation template from the [GitHub repository](https://github.com/lokesh8080/agentcore-memory-serverless) and try pushing your first session. For more information about Amazon Bedrock AgentCore Memory, see the [AgentCore Memory documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html).

---

**About the author**

Lokesh Bollapragada is a Technical Account Manager at AWS supporting public sector education customers. He specializes in operational excellence, cost optimization, and helping customers build well-architected cloud environments.
