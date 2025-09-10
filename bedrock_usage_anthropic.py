import boto3
import json

from config import region_name

bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region_name)


body = json.dumps(
    {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hi, How arw you?"
            }
        ]
    }
)

response = bedrock_client.invoke_model(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    body=body,
    contentType="application/json",
    accept="application/json"
)

# for anthropic input structure it mus contain this following things
"""
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [
        {
            "role": "system",
            "content":"System prompt"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
}
"""


#for anthropic output structure.
result = json.loads(response['body'].read())
text_result = result['content'][0]['text']
usage_result = result['usage'] # dict containing input_tokens and output tokens 

print(f"LLM Response: {text_result}")