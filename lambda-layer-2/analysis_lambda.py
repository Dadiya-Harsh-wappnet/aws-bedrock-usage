import json
import boto3
import time

DYNAMODB_TABLE = "agent-workflow-state"
NEXT_FUNCTION_NAME = "research-agent"  # Phase 3

def lambda_handler(event, context):
    # Initialize clients
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)
    bedrock = boto3.client('bedrock-runtime')
    lambda_client = boto3.client('lambda')

    # Extract session ID from event
    session_id = event.get('session_id')
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing session_id"})
        }

    # Fetch document content from DynamoDB
    response = table.get_item(Key={'session_id': session_id})
    if 'Item' not in response:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Session not found"})
        }

    document_content = response['Item'].get('document_content', '')
    if not document_content:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No document content found"})
        }

    # Prepare Bedrock prompt
    prompt = f"""
    Analyze the following document and extract:
    1. Key topics (max 5)
    2. Important entities (people, organizations, locations)
    3. Main themes
    4. Research questions that provide valuable context
    
    Document:
    {document_content}
    
    Respond in JSON format with keys: topics, entities, themes, research_questions
    """

    try:
        # Call Bedrock model
        response_text = invoke_bedrock_model(bedrock, prompt)
        analysis_result = json.loads(response_text)
    except Exception as e:
        update_workflow_error(session_id, f"Bedrock analysis failed: {str(e)}", table)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    # Store analysis results in DynamoDB
    table.update_item(
        Key={'session_id': session_id},
        UpdateExpression="SET workflow_stage=:stage, analysis_result=:result, extracted_topics=:topics, updated_at=:updated",
        ExpressionAttributeValues={
            ':stage': 'analysis_complete',
            ':result': analysis_result,
            ':topics': analysis_result.get('topics', []),
            ':updated': int(time.time())
        }
    )

    # Trigger next stage (Research Agent)
    try:
        lambda_client.invoke(
            FunctionName=NEXT_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps({'session_id': session_id})
        )
    except Exception as e:
        update_workflow_error(session_id, f"Failed to trigger research stage: {str(e)}", table)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Analysis complete", "session_id": session_id})
    }


# ------------------- Utility Functions -------------------

def invoke_bedrock_model(client, prompt, model_id="anthropic.claude-3-sonnet-20240229-v1:0", max_tokens=4000):
    """Invoke AWS Bedrock model"""
    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    })

    response = client.invoke_model(
        modelId=model_id,
        body=request_body,
        accept="application/json",
        contentType="application/json"
    )

    # Parse response
    response_json = json.loads(response['body'].read())
    return response_json['content'][0]['text']  # Claude response format


def update_workflow_error(session_id, error_message, table):
    """Mark workflow as error in DynamoDB"""
    table.update_item(
        Key={'session_id': session_id},
        UpdateExpression='SET workflow_stage=:stage, error_message=:err, updated_at=:updated',
        ExpressionAttributeValues={
            ':stage': 'error',
            ':err': error_message,
            ':updated': int(time.time())
        }
    )
