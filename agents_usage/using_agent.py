from boto3 import client

agent_client = client('bedrock-agent-runtime')

def complete_chat() -> str:
    """
    This method is an example to use agent    
    """
