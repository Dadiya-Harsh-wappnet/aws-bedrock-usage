import json
import boto3
import requests
import os
from typing import List, Dict, Any

def lambda_handler(event, context):
    session_id = event['session_id']
    dynamodb = boto3.resource('dynamodb')
    
    table = dynamodb.Table('agent-workflow-state')
    response = table.get_item(Key={'session_id': session_id})
    item = response['Item']
    
    research_questions = item.get('analysis_result', {}).get('research_questions', [])
    if not research_questions:
        return {"statusCode": 400, "body": "No research questions found"}
    
    findings = {}
    
    for question in research_questions:
        try:
            # Step 1: Fetch results from Tavily Web Search API
            raw_results = perform_tavily_search(question)
            
            # Step 2: Validate and summarize with Bedrock
            prompt = f"""
            You are a research assistant. Summarize the following search results for the question:
            
            Question: {question}
            Results: {json.dumps(raw_results, indent=2)}
            
            Provide a factual, concise answer in JSON format:
            {{
              "summary": "...",
              "reliability_score": "High/Medium/Low",
              "sources": ["url1", "url2"],
              "key_findings": ["finding1", "finding2"]
            }}
            """
            
            validated = invoke_bedrock_model(prompt, "anthropic.claude-3-sonnet-20240229-v1:0")
            findings[question] = validated
            
        except Exception as e:
            # Handle individual question failures gracefully
            findings[question] = {
                "summary": f"Error processing question: {str(e)}",
                "reliability_score": "Low",
                "sources": [],
                "key_findings": []
            }
    
    # Step 3: Store results in DynamoDB
    table.update_item(
        Key={'session_id': session_id},
        UpdateExpression="SET workflow_stage = :stage, research_findings = :findings, updated_at = :timestamp",
        ExpressionAttributeValues={
            ":stage": "research_complete",
            ":findings": findings,
            ":timestamp": context.aws_request_id  # Use request ID as timestamp
        }
    )
    
    # Step 4: Trigger Report Generation Agent
    return trigger_next_stage(session_id, "report-generation-agent")

# --- Tavily Web Search Functions ---

def perform_tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform web search using Tavily API
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of search results with title, url, content, and score
    """
    # Get Tavily API key from environment variables or AWS Systems Manager
    api_key = get_tavily_api_key()
    
    if not api_key:
        raise ValueError("Tavily API key not found")
    
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",  # or "basic" for faster results
        "include_answer": True,
        "include_raw_content": False,
        "max_results": max_results,
        "include_domains": [],  # Optional: specify domains to include
        "exclude_domains": []   # Optional: specify domains to exclude
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract and format results
        results = []
        if "results" in data:
            for result in data["results"]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                    "published_date": result.get("published_date", "")
                })
        
        # Include Tavily's answer if available
        tavily_answer = data.get("answer", "")
        if tavily_answer:
            results.insert(0, {
                "title": "Tavily AI Summary",
                "url": "tavily://answer",
                "content": tavily_answer,
                "score": 1.0,
                "published_date": ""
            })
        
        return results
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Tavily API request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Tavily API response: {str(e)}")

def get_tavily_api_key() -> str:
    """
    Get Tavily API key from environment variables or AWS Systems Manager
    
    Returns:
        API key string
    """
    # First try environment variable
    api_key = os.environ.get('TAVILY_API_KEY')
    if api_key:
        return api_key
    
    # Fallback to AWS Systems Manager Parameter Store
    try:
        ssm = boto3.client('ssm')
        parameter = ssm.get_parameter(
            Name='/lambda/tavily/api-key',
            WithDecryption=True
        )
        return parameter['Parameter']['Value']
    except Exception as e:
        print(f"Failed to get API key from Parameter Store: {str(e)}")
        return ""

# --- Enhanced Utility Functions ---

def invoke_bedrock_model(prompt: str, model_id: str) -> Dict[str, Any]:
    """
    Invoke Bedrock model with enhanced error handling
    """
    bedrock = boto3.client("bedrock-runtime")
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "temperature": 0.1,  # Low temperature for factual responses
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })
    
    try:
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get("body").read())
        content = response_body["content"][0]["text"]
        
        # Parse JSON response from Claude
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        # If Claude doesn't return valid JSON, create a fallback response
        return {
            "summary": "Error parsing model response",
            "reliability_score": "Low",
            "sources": [],
            "key_findings": []
        }
    except Exception as e:
        raise Exception(f"Bedrock model invocation failed: {str(e)}")

def trigger_next_stage(session_id: str, next_function: str) -> Dict[str, Any]:
    """
    Trigger the next stage in the workflow
    """
    try:
        lambda_client = boto3.client("lambda")
        
        payload = {
            "session_id": session_id,
            "previous_stage": "research_complete"
        }
        
        response = lambda_client.invoke(
            FunctionName=next_function,
            InvocationType="Event",
            Payload=json.dumps(payload)
        )
        
        return {
            "statusCode": 200, 
            "message": f"Successfully triggered {next_function}",
            "invocation_response": response.get('StatusCode')
        }
        
    except Exception as e:
        return {
            "statusCode": 500,
            "message": f"Failed to trigger {next_function}: {str(e)}"
        }