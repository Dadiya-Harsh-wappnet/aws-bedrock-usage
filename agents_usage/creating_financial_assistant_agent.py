from boto3 import client
from config import *

agent_client = client('bedrock-agent')

agent_instructions = """
You are a highly intelligent and reliable financial assistant. 
Your role is to provide clear, accurate, and practical financial advice, 
guiding the user in making informed decisions across various financial situations.
"""


response = agent_client.create_agent(
    agentName = "HarshFi-3",
    foundationModel = 'anthropic.claude-3-haiku-20240307-v1:0',
    agentResourceRoleArn = ROLE_AGENT_ARN,
    instruction = agent_instructions
)
print(f"Result is: {response}\n \n")

result = response['agent']

print(result)