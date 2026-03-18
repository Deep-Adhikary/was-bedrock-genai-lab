from bedrock_agentcore.runtime import (
    BedrockAgentCoreApp,
)  #### AGENTCORE RUNTIME - LINE 1 ####
from strands import Agent
from strands.models import BedrockModel
from scripts.utils import get_ssm_parameter
from retrying import retry
from lab_helpers.lab1_strands_agent import (
    get_return_policy,
    get_product_info,
    get_technical_support,
    SYSTEM_PROMPT,
    MODEL_ID,
)

from lab_helpers.lab2_memory import (
    CustomerSupportMemoryHooks,
    memory_client,
    ACTOR_ID,
    SESSION_ID,
)

# Retry logic for handling throttling and service unavailable errors
def should_retry(exception):
    error_str = str(exception).lower()
    return 'throttl' in error_str or 'serviceunavailable' in error_str

@retry(retry_on_exception=should_retry,
       wait_fixed=5000,
       stop_max_delay=30*1000)
def call_with_retry(f):
    return f()

# Lab1 import: Create the Bedrock model
model = BedrockModel(model_id=MODEL_ID)

# Lab2 import : Initialize memory via hooks
memory_id = get_ssm_parameter("/app/customersupport/agentcore/memory_id")
memory_hooks = CustomerSupportMemoryHooks(
    memory_id, memory_client, ACTOR_ID, SESSION_ID
)

# Create the agent with all customer support tools
agent = Agent(
    model=model,
    tools=[get_return_policy, get_product_info, get_technical_support],
    system_prompt=SYSTEM_PROMPT,
    hooks=[memory_hooks],
)

# Initialize the AgentCore Runtime App
app = BedrockAgentCoreApp()  #### AGENTCORE RUNTIME - LINE 2 ####


@app.entrypoint  #### AGENTCORE RUNTIME - LINE 3 ####
def invoke(payload):
    """AgentCore Runtime entrypoint function"""
    user_input = payload.get("prompt", "")

    # Invoke the agent with retry logic
    response = call_with_retry(lambda: agent(user_input))
    return response.message["content"][0]["text"]

if __name__ == "__main__":
    app.run()  #### AGENTCORE RUNTIME - LINE 4 ####
