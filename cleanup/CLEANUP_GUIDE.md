# PACE Bootcamp Cleanup Guide

## Overview

The `01_cleanup.ipynb` notebook provides comprehensive cleanup for all PACE Bootcamp resources, including both general workshop resources and AgentCore-specific resources.

## What Gets Cleaned Up

### 1. Tagged Resources (Step 2)
- All AWS resources tagged with `app:pace_bootcamp`
- Uses the `cleanup_tagged_resources` module

### 2. AgentCore-Specific Resources (Step 3.1-3.4)
**Only runs if AgentCore labs were completed**

- **Memory (3.1)**: AgentCore Memory resources and stored conversation data
- **Gateway (3.2)**: Gateway targets and MCP endpoints
- **Runtime (3.3)**: Agent runtime instances and ECR repositories
- **Security (3.4)**: IAM execution roles, Cognito user pools, SSM parameters, Secrets Manager secrets

### 3. General Untagged Resources (Step 3.5-3.9)
- **S3 Vectors (3.5)**: Vector buckets and indexes
- **AgentCore Runtimes (3.6)**: Any remaining runtime instances
- **ECR Repositories (3.7)**: Container image repositories
- **Secrets Manager (3.8)**: Application secrets
- **CodeBuild (3.9)**: Build projects

### 4. Infrastructure & Cleanup (Step 3.10-3.12)
- **CloudWatch Logs (3.10)**: Log groups and streams
- **CloudFormation Stacks (3.11)**: Infrastructure and Cognito stacks, S3 bucket, Lambda deployment artifacts
- **Local Files (3.12)**: Generated configuration files in AgentCore directory

## How It Works

### Intelligent Detection
The notebook automatically detects if AgentCore labs were completed:

```python
# Tries to import AgentCore utilities
try:
    from lab_helpers.utils import (...)
    AGENTCORE_AVAILABLE = True
except ImportError:
    AGENTCORE_AVAILABLE = False
```

### Conditional Cleanup
AgentCore-specific cleanup only runs if utilities are available:

```python
if AGENTCORE_AVAILABLE:
    # Run AgentCore cleanup
else:
    # Skip with informational message
```

### Error Handling
Each cleanup section has try-except blocks to continue even if errors occur:

```python
try:
    cleanup_function()
    print("✅ Cleanup completed")
except Exception as e:
    print(f"⚠️  Error: {e}")
```

## Usage

### Running the Full Cleanup

1. Open `labs/cleanup/01_cleanup.ipynb`
2. Run all cells sequentially
3. Review the completion summary

### Running Selective Cleanup

You can run individual sections by executing specific cells:
- Run only Step 2 for tagged resources
- Run only Step 3.1-3.4 for AgentCore resources
- Run only Step 3.5-3.9 for general resources

## What Was Merged

### From `lab-06-cleanup.ipynb`
The following AgentCore-specific cleanup functions were integrated:

1. **Memory Cleanup** (`agentcore_memory_cleanup`)
   - Lists all memories
   - Deletes memory resources
   - Removes SSM parameters

2. **Gateway Cleanup** (`gateway_target_cleanup`)
   - Lists gateway targets
   - Deletes all targets
   - Removes gateway endpoints

3. **Runtime Cleanup** (`runtime_resource_cleanup`)
   - Deletes agent runtimes
   - Removes ECR repositories
   - Cleans up container images

4. **Security Cleanup**
   - Deletes IAM execution roles
   - Removes Cognito user pools and clients
   - Deletes Secrets Manager secrets
   - Cleans up SSM parameters

5. **Observability Cleanup** (`delete_observability_resources`)
   - Deletes CloudWatch log groups
   - Removes log streams

6. **CloudFormation Stack Cleanup**
   - Deletes CustomerSupportStackInfra (Lambda, DynamoDB, IAM roles)
   - Deletes CustomerSupportStackCognito (User pools, clients)
   - Empties and deletes S3 deployment bucket
   - Removes local lambda.zip file

7. **Local Files Cleanup** (`local_file_cleanup`)
   - Removes generated Dockerfiles
   - Deletes configuration files
   - Cleans up Python scripts

### From Original `01_cleanup.ipynb`
All original functionality was preserved:

1. **Tagged Resource Cleanup**
   - Uses existing `cleanup_tagged_resources` module
   - Maintains original workflow

2. **S3 Vectors Cleanup**
   - Deletes vector buckets and indexes
   - Preserved original logic

3. **General Resource Cleanup**
   - ECR repositories
   - Secrets Manager
   - CodeBuild projects
   - AgentCore runtimes (enhanced with AgentCore-specific logic)

4. **CloudFormation Stack Cleanup**
   - Infrastructure stack (Lambda, DynamoDB, IAM)
   - Cognito stack (User pools, clients)
   - S3 deployment bucket
   - Local deployment artifacts

## Benefits of the Merge

### Single Cleanup Location
- One notebook for all cleanup operations
- No need to run multiple cleanup notebooks
- Consistent cleanup experience

### Intelligent Execution
- Automatically detects which labs were completed
- Skips irrelevant cleanup steps
- Provides clear feedback on what's being cleaned

### Comprehensive Coverage
- Handles both tagged and untagged resources
- Covers all AWS services used in the bootcamp
- Deletes CloudFormation stacks and infrastructure
- Includes local file cleanup

### Error Resilience
- Continues cleanup even if individual steps fail
- Provides detailed error messages
- Shows completion summary at the end

## Troubleshooting

### "AgentCore utilities not available"
**Cause**: AgentCore labs were not completed or path is incorrect

**Solution**: This is normal if you didn't complete AgentCore labs. The cleanup will skip AgentCore-specific steps.

### "Resource not found" errors
**Cause**: Resources were already deleted or never created

**Solution**: These are informational messages. The cleanup continues with remaining resources.

### Permission errors
**Cause**: Insufficient IAM permissions

**Solution**: Ensure your AWS credentials have permissions to delete all resource types.

## Verification

After running cleanup, verify resources are deleted:

```bash
# Check AgentCore resources
aws bedrock-agentcore-control list-agent-runtimes
aws bedrock-agentcore-control list-gateways
aws bedrock-agentcore-control list-memories

# Check ECR repositories
aws ecr describe-repositories

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/bedrock-agentcore/

# Check tagged resources
aws resourcegroupstaggingapi get-resources --tag-filters Key=app,Values=pace_bootcamp
```

## Cost Considerations

Running this cleanup will:
- ✅ Stop ongoing charges for running resources
- ✅ Remove stored data (logs, memory, vectors)
- ✅ Delete container images
- ⚠️  Some resources may have minimum retention periods
- ⚠️  CloudWatch logs may incur small storage costs until fully deleted

## Support

If you encounter issues:
1. Check the error messages in the notebook output
2. Verify your AWS credentials and permissions
3. Review the AWS Console for any remaining resources
4. Manually delete any stuck resources using the AWS Console

## Related Files

- `labs/cleanup/01_cleanup.ipynb` - Main cleanup notebook
- `labs/cleanup/cleanup_tagged_resources.py` - Tagged resource cleanup module
- `labs/agentcore/lab_helpers/utils.py` - AgentCore cleanup utilities
- `labs/agentcore/lab-06-cleanup.ipynb` - Original AgentCore cleanup (now deprecated)
