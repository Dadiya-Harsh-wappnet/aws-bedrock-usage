import json
import boto3
import time
from datetime import datetime

def lambda_handler(event, context):
    session_id = event['session_id']
    dynamodb = boto3.resource("dynamodb")
    s3 = boto3.client("s3")
    
    table = dynamodb.Table("agent-workflow-state")
    response = table.get_item(Key={"session_id": session_id})
    item = response["Item"]

    # Collect inputs
    analysis_result = item.get("analysis_result", {})
    research_findings = item.get("research_findings", {})
    document_content = item.get("document_content", "")

    # Build prompt
    report_prompt = f"""
    You are a professional research report writer.
    
    Create a detailed research report using the following information:
    
    - Original Document:
    {document_content[:1000]}...
    
    - Document Analysis:
    {json.dumps(analysis_result, indent=2)}
    
    - Research Findings:
    {json.dumps(research_findings, indent=2)}
    
    Structure the report with:
    1. Executive Summary
    2. Key Findings
    3. Detailed Analysis
    4. Supporting Research
    5. Conclusions and Recommendations
    
    Write in clear, professional English.
    """

    # Call Bedrock
    report_text = invoke_bedrock_model(report_prompt, "anthropic.claude-3-haiku-20240307-v1:0")

    # Store report in S3
    bucket_name = "learningawswithdadiyaharshwappnet"
    report_key = f"reports/{session_id}_report_{int(time.time())}.txt"

    s3.put_object(
        Bucket=bucket_name,
        Key=report_key,
        Body=report_text.encode("utf-8"),
        ContentType="text/plain"
    )

    # Update DynamoDB
    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression="SET workflow_stage = :stage, final_report = :report, updated_at = :ts",
        ExpressionAttributeValues={
            ":stage": "report_generated",
            ":report": report_text,
            ":ts": int(time.time())
        }
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Report generated successfully",
            "session_id": session_id,
            "report_s3_url": f"s3://{bucket_name}/{report_key}"
        })
    }

# --- Utility Function ---
def invoke_bedrock_model(prompt, model_id):
    bedrock = boto3.client("bedrock-runtime")

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })

    response = bedrock.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(response.get("body").read())
    return response_body["content"][0]["text"]
