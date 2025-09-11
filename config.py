import os 
from dotenv import load_dotenv
load_dotenv()


AWS_BEARER_TOKEN_BEDROCK = os.getenv('AWS_BEARER_TOKEN_BEDROCK')
ACCESS_KEY_ID = os.getenv('ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('SECRET_ACCESS_KEY')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')
region_name = os.getenv('region_name')
ROLE_AGENT_ARN = os.getenv('ROLE_AGENT_ARN')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')