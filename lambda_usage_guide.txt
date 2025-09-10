## 📝 AWS Lambda Deployment Workflow

### 1. **Create a Lambda Layer**

Use layers to package dependencies.

```bash
# Install dependencies into a folder
pip install -r requirements.txt -t python/

# Zip the folder
zip -r layer.zip python/

# Publish the layer
aws lambda publish-layer-version \
    --layer-name my-layer-name \
    --zip-file fileb://layer.zip \
    --compatible-runtimes python3.11
```

---

### 2. **Write Lambda Function**

Create a file (example: `analysis_lambda.py`):

```python
def lambda_handler(event, context):
    # Your logic here
    return {"status": "success"}
```

---

### 3. **Package and Deploy Function**

Zip the function code and create the Lambda.

```bash
zip function.zip analysis_lambda.py

aws lambda create-function \
  --function-name analysis-agent \
  --runtime python3.11 \
  --role arn:aws:iam::<account_id>:role/BEDROCK_USAGE_ROLE \
  --handler analysis_lambda.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment "Variables={DYNAMODB_TABLE=agent-workflow-state,NEXT_FUNCTION_NAME=research-agent}" \
  --region <region>
```

---

### 4. **Attach the Layer**

Link the function to your dependency layer:

```bash
aws lambda update-function-configuration \
    --function-name analysis-agent \
    --layers arn:aws:lambda:<region>:<account_id>:layer:my-layer-name:1
```

---

### 5. **Invoke/Test the Function**

Test with an S3 event payload.

```bash
aws lambda invoke \
  --function-name document-ingestion-agent \
  --payload '{
    "Records": [
      {
        "eventSource": "aws:s3",
        "s3": {
          "bucket": { "name": "<bucket-name>" },
          "object": { "key": "insight-report.pdf" }
        }
      }
    ]
  }' \
  --cli-binary-format raw-in-base64-out \
  output.json
```

✅ Example Output:

```json
{
  "StatusCode": 200,
  "ExecutedVersion": "$LATEST"
}
```

---

⚡ This workflow ensures:

1. Dependencies in a **layer**
2. Function packaged separately
3. Layer attached to function
4. Function tested with a sample payload
