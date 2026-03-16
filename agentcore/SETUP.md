# AgentCore Labs Setup Guide

## Quick Start

**Step 1: Run Infrastructure Setup (Required)**

Before starting the labs, deploy the required AWS infrastructure:

1. Open `lab-01-create-an-agent.ipynb`
2. Find the "Setup Required Infrastructure" section (near the top)
3. Run the cell: `!bash scripts/prereq.sh`
4. Wait ~5-10 minutes for deployment to complete
5. Run the verification cell to confirm everything deployed

**What Gets Deployed:**
- AWS Lambda functions (warranty check, web search)
- DynamoDB tables (warranty data, customer profiles)
- IAM roles (Gateway, Runtime, Lambda execution)
- Amazon Cognito User Pool (authentication)
- SSM Parameters (configuration storage)

**Step 2: Proceed Through Labs**

Once infrastructure is deployed, proceed through labs in order:
- Lab 1: Create Agent (no infrastructure needed)
- Lab 2: Add Memory (creates memory resources on-demand)
- Lab 3: Add Gateway (requires Lab 1 infrastructure)
- Lab 4: Deploy Runtime (requires Lab 1 infrastructure)
- Lab 5: Build Frontend (requires Lab 1 infrastructure)

## Infrastructure Dependencies

| Lab | Requires Infrastructure | Notes |
|-----|------------------------|-------|
| Lab 1 | ❌ No | Uses only local tools |
| Lab 2 | ⚠️ Optional | Creates Memory resources on-demand |
| Lab 3 | ✅ Yes | Needs Lambda, Cognito, DynamoDB |
| Lab 4 | ✅ Yes | Needs IAM roles, Lambda |
| Lab 5 | ✅ Yes | Needs all resources |

## Troubleshooting

### "Parameter not found" errors in Lab 3+
**Solution:** Go back to Lab 1 and run the `prereq.sh` script cell.

### "Stack already exists" error
**Solution:** Infrastructure is already deployed. Continue with labs.

### Deployment fails
**Solution:** Check:
- AWS credentials are configured (`aws sts get-caller-identity`)
- You have permissions to create CloudFormation stacks
- Region supports Amazon Bedrock (us-east-1, us-west-2, etc.)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Lab 1: Local Agent (No Infrastructure)                     │
│  ┌──────────┐                                               │
│  │  Agent   │ ──> Local Tools                               │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Lab 2: Agent + Memory (Creates on-demand)                   │
│  ┌──────────┐      ┌─────────────────┐                     │
│  │  Agent   │ ───> │ AgentCore Memory│                     │
│  └──────────┘      └─────────────────┘                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Lab 3+: Full Infrastructure (Requires prereq.sh)            │
│  ┌──────────┐      ┌─────────────────┐                     │
│  │  Agent   │ ───> │ AgentCore Gateway│                    │
│  └──────────┘      └─────────────────┘                     │
│                            │                                 │
│                            ├──> Lambda (Tools)               │
│                            ├──> DynamoDB (Data)              │
│                            └──> Cognito (Auth)               │
└─────────────────────────────────────────────────────────────┘
```