'''
This module or script demonstrates how to use the multiple agents from the strands-agents library, 
specifically with OpenAI or any other OpenAI-compatible SDK like Groq.
Since the strands-agents library has more features and is more user-friendly, i would recommended to use it for building agents.
'''
import requests
import json
from pydantic import BaseModel
from typing import List, Union
import logging

from config import FIRECRAWL_API_KEY, OPENAI_API_KEY, GROQ_API_KEY

from strands import Agent, tool

looger = logging.getLogger(__name__)
looger.setLevel(logging.INFO)
ch = logging.StreamHandler()

class ResponseFormat(BaseModel):
    """This is the response format for the agent that i want.
    Args:
        BaseModel (_type_): _description_
    Attributes:
        result (str): The final answer or result produced by the agent.
        reasoning (str): The reasoning process or thought steps taken by the agent to arrive at the result.
        steps_to_solution (Union[str, List[str]]): A detailed breakdown of the steps taken to reach the solution. This can be a single string or a list of strings.
        tools_used (Union[str, List[str]]): Information about any tools that were utilized during the process. This can be a single string or a list of strings.
        tool_responses (Union[str, List[str]]): The responses received from the tools that were used. This can be a single string or a list of strings.
    """
    result: str
    reasoning: str
    steps_to_solution: Union[str, List[str]]
    tools_used: Union[str, List[str]]
    tool_responses: Union[str, List[str]]
    

@tool
def crawl_website(
    url: str,
    query: str
) -> dict:
    """
    A tool to crawl a website and extract relevant information based on a query usinf firecrawl.
    Args:
        url (str): The URL of the website to crawl.
        query (str): The specific information or topic to search for on the website.
        
    Returns:
        dict: The crawled data and relevant information extracted from the website.
    """
    try:
        base_url = "https://api.firecrawl.dev/v2/crawl"

        payload = {
        "url": url,
        "sitemap": "include",
        "crawlEntireDomain": True,
        "prompt":  query,
        "scrapeOptions": {
                "onlyMainContent": True,
                "maxAge": 172800000,
                "parsers": [
                "pdf"
                ],
                "formats": [
                "markdown"
                ]
            }
        }

        headers = {
            f"Authorization": "Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(base_url, json=payload, headers=headers)
        
        response_json = response.json()

        looger.info(f"Your request status has been submitted and this is id: {response_json.get('id')}")
        
        result_base_url =f"https://api.firecrawl.dev/v2/crawl/{response_json.get('id')}"
        
        result_header ={
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        }
        
        final_respnse = requests.get(result_base_url, headers =result_header)
        
        looger.info(f"Your request is completed with status: {final_respnse.json().get('status')}")
        
        
        # now return the final response json
        return final_respnse.json()
    except Exception as e:
        looger.error(f"Error occurred while crawling the website: {e}")
        return {"error": str(e)}
    