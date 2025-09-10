import json
import boto3
import time
import os
import hashlib
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional

# Optional imports with fallback handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("WARNING: PyPDF2 not available - PDF processing will be limited")

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("WARNING: python-docx not available - Word document processing disabled")

# Environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'agent-workflow-state')
NEXT_FUNCTION_NAME = os.environ.get('NEXT_FUNCTION_NAME', 'analysis-agent')
MAX_CONTENT_SIZE = int(os.environ.get('MAX_CONTENT_SIZE', '50000'))  # Max chars to store in DynamoDB

class DocumentProcessor:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.lambda_client = boto3.client('lambda')
        self.table = self.dynamodb.Table(DYNAMODB_TABLE)
        
    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using PyPDF2"""
        if not PDF_SUPPORT:
            return "ERROR: PDF processing not available - PyPDF2 library not installed"
        
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text_content = []
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text.strip():  # Only add non-empty pages
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as page_error:
                    print(f"Error extracting text from page {page_num + 1}: {str(page_error)}")
                    text_content.append(f"--- Page {page_num + 1} ---\n[Error extracting page content]")
            
            full_text = "\n\n".join(text_content)
            
            # Basic validation
            if len(full_text.strip()) < 10:
                return "WARNING: Extracted text is very short - PDF might be image-based or protected"
            
            return full_text
            
        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            print(error_msg)
            return error_msg
    
    def extract_docx_text(self, docx_bytes: bytes) -> str:
        """Extract text from Word document bytes"""
        if not DOCX_SUPPORT:
            return "ERROR: Word document processing not available - python-docx library not installed"
        
        try:
            doc = Document(BytesIO(docx_bytes))
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            full_text = "\n".join(paragraphs)
            
            if len(full_text.strip()) < 10:
                return "WARNING: Extracted text is very short - document might be empty"
            
            return full_text
            
        except Exception as e:
            error_msg = f"Error processing Word document: {str(e)}"
            print(error_msg)
            return error_msg
    
    def extract_text_content(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extract text content based on file type with metadata"""
        file_extension = self._get_file_extension(filename)
        file_size = len(file_bytes)
        
        extraction_result = {
            'filename': filename,
            'file_extension': file_extension,
            'file_size': file_size,
            'extraction_method': 'unknown',
            'extraction_success': False,
            'content': '',
            'metadata': {},
            'warnings': []
        }
        
        try:
            if file_extension.lower() == '.pdf':
                extraction_result['content'] = self.extract_pdf_text(file_bytes)
                extraction_result['extraction_method'] = 'PyPDF2'
                
            elif file_extension.lower() in ['.docx', '.doc']:
                if file_extension.lower() == '.docx':
                    extraction_result['content'] = self.extract_docx_text(file_bytes)
                    extraction_result['extraction_method'] = 'python-docx'
                else:
                    extraction_result['content'] = "ERROR: .doc files not supported, please convert to .docx"
                    extraction_result['warnings'].append("Legacy .doc format not supported")
                    
            elif file_extension.lower() in ['.txt', '.md', '.csv']:
                # Try different encodings
                for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        extraction_result['content'] = file_bytes.decode(encoding)
                        extraction_result['extraction_method'] = f'text_decode_{encoding}'
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    extraction_result['content'] = file_bytes.decode('utf-8', errors='ignore')
                    extraction_result['extraction_method'] = 'text_decode_fallback'
                    extraction_result['warnings'].append("Used fallback encoding - some characters might be corrupted")
                    
            elif file_extension.lower() in ['.json']:
                try:
                    json_content = json.loads(file_bytes.decode('utf-8'))
                    extraction_result['content'] = json.dumps(json_content, indent=2)
                    extraction_result['extraction_method'] = 'json_parse'
                    extraction_result['metadata']['json_keys'] = list(json_content.keys()) if isinstance(json_content, dict) else None
                except json.JSONDecodeError as e:
                    extraction_result['content'] = f"ERROR: Invalid JSON file - {str(e)}"
                    
            else:
                # Try to decode as text with fallback
                try:
                    extraction_result['content'] = file_bytes.decode('utf-8')
                    extraction_result['extraction_method'] = 'generic_text'
                    extraction_result['warnings'].append(f"Unsupported file type {file_extension}, treated as text")
                except UnicodeDecodeError:
                    extraction_result['content'] = file_bytes.decode('utf-8', errors='ignore')
                    extraction_result['extraction_method'] = 'generic_text_fallback'
                    extraction_result['warnings'].append(f"Unsupported file type {file_extension}, used fallback text extraction")
            
            # Check if extraction was successful
            if extraction_result['content'] and not extraction_result['content'].startswith('ERROR:'):
                extraction_result['extraction_success'] = True
                
            # Add content statistics
            content = extraction_result['content']
            extraction_result['metadata'].update({
                'content_length': len(content),
                'word_count': len(content.split()) if content else 0,
                'line_count': content.count('\n') + 1 if content else 0,
                'has_content': len(content.strip()) > 0
            })
            
        except Exception as e:
            extraction_result['content'] = f"ERROR: Failed to process file - {str(e)}"
            extraction_result['warnings'].append(f"Unexpected error during extraction: {str(e)}")
        
        return extraction_result
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return '.' + filename.split('.')[-1] if '.' in filename else ''
    
    def _generate_session_id(self, filename: str, content: str) -> str:
        """Generate unique session ID based on filename and content hash"""
        base_name = filename.split('.')[0] if '.' in filename else filename
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        
        return f"{base_name}_{content_hash}_{timestamp}"
    
    def store_document_data(self, session_id: str, extraction_result: Dict[str, Any], bucket: str, key: str) -> bool:
        """Store document data in DynamoDB"""
        try:
            content = extraction_result['content']
            
            # Truncate content if too large for DynamoDB
            stored_content = content[:MAX_CONTENT_SIZE] if len(content) > MAX_CONTENT_SIZE else content
            content_truncated = len(content) > MAX_CONTENT_SIZE
            
            item = {
                'session_id': session_id,
                'workflow_stage': 'document_processed',
                'document_content': stored_content,
                'content_truncated': content_truncated,
                'full_content_length': len(content),
                'original_filename': extraction_result['filename'],
                'file_type': extraction_result['file_extension'],
                'file_size': extraction_result['file_size'],
                'extraction_method': extraction_result['extraction_method'],
                'extraction_success': extraction_result['extraction_success'],
                'extraction_warnings': extraction_result['warnings'],
                'content_metadata': extraction_result['metadata'],
                's3_bucket': bucket,
                's3_key': key,
                'created_at': int(time.time()),
                'updated_at': int(time.time()),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
            # Add optional fields if they exist
            if content_truncated:
                item['full_content_s3_location'] = f"s3://{bucket}/{key}"
            
            self.table.put_item(Item=item)
            
            print(f"Successfully stored document data for session: {session_id}")
            print(f"Content length: {len(content)}, Stored length: {len(stored_content)}")
            
            return True
            
        except Exception as e:
            print(f"Error storing document data: {str(e)}")
            return False
    
    def trigger_next_stage(self, session_id: str) -> bool:
        """Trigger the next Lambda function (Analysis stage)"""
        try:
            payload = {
                'session_id': session_id,
                'trigger_source': 'document_ingestion',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.lambda_client.invoke(
                FunctionName=NEXT_FUNCTION_NAME,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            print(f"Successfully triggered next stage function: {NEXT_FUNCTION_NAME}")
            print(f"Session ID: {session_id}")
            
            return True
            
        except Exception as e:
            print(f"Error triggering next stage: {str(e)}")
            # Update DynamoDB to record the error
            self._update_error_state(session_id, f"Failed to trigger analysis stage: {str(e)}")
            return False
    
    def _update_error_state(self, session_id: str, error_message: str):
        """Update workflow state to indicate error"""
        try:
            self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET workflow_stage = :stage, error_message = :error, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':stage': 'error_document_processing',
                    ':error': error_message,
                    ':timestamp': int(time.time())
                }
            )
        except Exception as e:
            print(f"Error updating error state: {str(e)}")

def lambda_handler(event, context):
    """Main Lambda handler for document ingestion"""
    print(f"Document Ingestion Lambda started at {datetime.utcnow().isoformat()}")
    print(f"Event: {json.dumps(event, default=str)}")
    
    processor = DocumentProcessor()
    
    try:
        # Handle S3 trigger event
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:s3':
                    # S3 event trigger
                    bucket = record['s3']['bucket']['name']
                    key = record['s3']['object']['key']
                    
                    print(f"Processing S3 object: s3://{bucket}/{key}")
                    
                    # Skip non-document files
                    if not any(key.lower().endswith(ext) for ext in ['.pdf', '.txt', '.docx', '.doc', '.md', '.json', '.csv']):
                        print(f"Skipping unsupported file type: {key}")
                        continue
                    
                    # Get document from S3
                    try:
                        s3_response = processor.s3_client.get_object(Bucket=bucket, Key=key)
                        file_bytes = s3_response['Body'].read()
                        
                        print(f"Retrieved file: {key}, Size: {len(file_bytes)} bytes")
                        
                    except Exception as e:
                        print(f"Error retrieving S3 object: {str(e)}")
                        continue
                    
                    # Extract text content
                    extraction_result = processor.extract_text_content(file_bytes, key)
                    
                    if not extraction_result['extraction_success']:
                        print(f"Text extraction failed for {key}: {extraction_result['content']}")
                        continue
                    
                    # Generate session ID
                    session_id = processor._generate_session_id(key, extraction_result['content'])
                    
                    print(f"Generated session ID: {session_id}")
                    
                    # Store in DynamoDB
                    if processor.store_document_data(session_id, extraction_result, bucket, key):
                        # Trigger next stage
                        processor.trigger_next_stage(session_id)
                    else:
                        print(f"Failed to store document data for session: {session_id}")
        
        # Handle direct invocation (for testing)
        elif 'bucket' in event and 'key' in event:
            bucket = event['bucket']
            key = event['key']
            
            print(f"Direct invocation - Processing: s3://{bucket}/{key}")
            
            # Process single file
            s3_response = processor.s3_client.get_object(Bucket=bucket, Key=key)
            file_bytes = s3_response['Body'].read()
            
            extraction_result = processor.extract_text_content(file_bytes, key)
            session_id = processor._generate_session_id(key, extraction_result['content'])
            
            if processor.store_document_data(session_id, extraction_result, bucket, key):
                processor.trigger_next_stage(session_id)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Document processed successfully',
                        'session_id': session_id,
                        'extraction_success': extraction_result['extraction_success'],
                        'content_length': len(extraction_result['content']),
                        'warnings': extraction_result['warnings']
                    })
                }
        
        else:
            print("Invalid event format - expected S3 trigger or direct invocation")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Document ingestion completed'})
        }
        
    except Exception as e:
        print(f"Unexpected error in document ingestion: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For testing locally
# if __name__ == "__main__":
#     # Test event for local development
#     test_event = {
#         'bucket': 'your-test-bucket',
#         'key': 'test-document.pdf'
#     }
    
#     test_context = {}
#     result = lambda_handler(test_event, test_context)