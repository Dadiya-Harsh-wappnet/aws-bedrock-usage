"""
This is simple example how to use the strands-agents with OpenAI or any other openai compatible sdk like Groq.
"""

from strands import Agent
from strands.models.openai import OpenAIModel
from config import OPENAI_API_KEY, GROQ_API_KEY

import asyncio

#if you want to use openai directly then replace api key and model_id below and comment base_url parameter or remove it.

model = OpenAIModel(
    client_args={
        "api_key": GROQ_API_KEY,
        "base_url": "https://api.groq.com/openai/v1"
    },
    model_id="openai/gpt-oss-120b"
)

async def main():

    while True:
        input_text = input("You: ")
        if input_text.lower() in ['exit', 'quit', 'q']:
            print("Exiting...")
            break
        agent = Agent(
            model=model
        )
        
        # you can also use agent() directly  or use below invoke_async method
        response_agent = await agent.invoke_async(
            input_text  
        )

        # if you directly print response_agent it will print the response text only
        # message is a dict which contains a dict messages happened between user and agent in the conversation
        print(type(response_agent.messages))
        response = response_agent.message.get('content')[0]['text']
        
        # to see summary of metrics including token usage in dict format.
        usage_summary = response_agent.metrics.get_summary()
        print(f"Token Usage: {usage_summary}")

        print(response)
    
if __name__ == "__main__":
    asyncio.run(main())
    
    # run in terminal using `python strands_agents/openai_usage.py`
    # or `python -u -m strands_agents.openai_usage``
    # -u for unbuffered output, useful for seeing prints in real-time