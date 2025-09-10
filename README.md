# AWS Bedrock Usage

This repository demonstrates advanced usage and orchestration of AWS Bedrock for document analysis, research automation, and agent-based workflows. It includes Lambda layers for document extraction, financial assistant agent creation, research automation, and report generation, leveraging Bedrock LLMs (such as Claude 3) and third-party APIs (like Tavily for web search).

## Features

- **Document Processing**: Extract text and metadata from documents (PDF, DOCX, and more) using Lambda functions.
- **Automated Analysis**: Analyze documents for key topics, entities, themes, and research questions using AWS Bedrock LLMs.
- **Research Automation**: Integrate Tavily API for web search and validate findings using Bedrock models.
- **Agent Creation**: Code examples to create and use intelligent agents (e.g., financial assistant) with Anthropic Claude on Bedrock.
- **Report Generation**: Automatically generate structured research reports from processed and analyzed documents.
- **AWS Integration**: Utilizes S3 and DynamoDB for storage, state management, and workflow orchestration.
- **Extensible Lambda Layers**: Modular architecture for custom Lambda layers and functions.

## Directory Overview

- `lambda-layer-1/` — Document extraction and DynamoDB integration.
- `lambda-layer-2/` — Document analysis using LLMs.
- `lambda-layer-3/` — Research automation with Tavily web search and Bedrock validation.
- `lambda-layer-4/` — Report generation and workflow management.
- `agents_usage/` — Agent creation and usage examples.
- `bedrock_usage_anthropic.py` — Sample usage of Anthropic Claude via Bedrock.

## Setup

1. **AWS Credentials**: Configure your AWS credentials with appropriate permissions for Lambda, Bedrock, DynamoDB, and S3.
2. **Environment Variables**: Set any necessary environment variables (e.g., Tavily API key).
3. **Dependencies**: Install required Python packages (see code comments for `boto3`, `PyPDF2`, etc.).
4. **Deployment**: Deploy Lambda functions and layers via AWS Console, SAM, or CDK as needed.

## Example Usage

- **Document Extraction & Analysis:** Upload a file to S3 and trigger the Lambda workflow to extract, analyze, and store results.
- **Agent Creation:** Use the provided examples to spin up a Bedrock agent for financial or research tasks.
- **Research Automation:** Run the research Lambda to fetch and validate web research findings.

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Author:** @Dadiya-Harsh-wappnet
