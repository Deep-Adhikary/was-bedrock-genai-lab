import os
import time
import boto3
from urllib.parse import urlparse
import requests
import json
from botocore.exceptions import ClientError
import pymupdf
from PIL import Image
from IPython.display import display, Image as IPImage


def get_bucket_and_key(s3_uri):
    """Extract bucket name and key from S3 URI"""
    parsed_uri = urlparse(s3_uri)
    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    return (bucket_name, object_key)


def read_s3_object(s3_uri):
    """Read content from S3 object"""
    s3_client = boto3.client('s3')
    bucket_name, object_key = get_bucket_and_key(s3_uri)
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        print(f"Error reading S3 object: {e}")
        return None


def wait_for_job_to_complete(invocation_arn, max_iterations=15, delay=30):
    """Wait for BDA job to complete and return status"""
    bda_runtime_client = boto3.client('bedrock-data-automation-runtime')
    
    for iteration in range(max_iterations):
        try:
            response = bda_runtime_client.get_data_automation_status(
                invocationArn=invocation_arn
            )
            status = response['status']
            
            if status == 'Success':
                print(f"Job completed after {iteration + 1} iterations")
                return response
            elif status in ['ClientError', 'ServiceError']:
                raise Exception(f"Job failed with status: {status}")
            
            print(f"Iteration {iteration + 1}: Status is {status}, waiting...")
            time.sleep(delay)
            
        except Exception as e:
            raise Exception(f"Error checking job status: {str(e)}")
    
    raise Exception(f"Job timed out after {max_iterations} iterations")


def wait_for_project_completion(project_arn, max_iterations=15, delay=30):
    """Wait for project creation/update to complete"""
    bda_client = boto3.client('bedrock-data-automation')
    
    for iteration in range(max_iterations):
        try:
            response = bda_client.get_data_automation_project(projectArn=project_arn)
            status = response['project']['status']
            
            if status == 'COMPLETED':
                print(f"Project ready after {iteration + 1} iterations")
                return response
            elif status == 'FAILED':
                raise Exception(f"Project creation failed")
            
            print(f"Iteration {iteration + 1}: Project status is {status}, waiting...")
            time.sleep(delay)
            
        except Exception as e:
            raise Exception(f"Error checking project status: {str(e)}")
    
    raise Exception(f"Project creation timed out after {max_iterations} iterations")


def download_document(url, output_file_path, verify=True):
    """Download document from URL
    
    Args:
        url: URL to download from
        output_file_path: Local path to save the file
        verify: Whether to verify SSL certificates (default: True)
    """
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    response = requests.get(url, timeout=30, verify=verify)
    response.raise_for_status()
    
    with open(output_file_path, 'wb') as f:
        f.write(response.content)
    
    print(f"Downloaded document to: {output_file_path}")
    return output_file_path


def create_or_update_blueprint(blueprint_name, blueprint_description, blueprint_type, blueprint_stage, blueprint_schema):
    """Create or update a blueprint"""
    bda_client = boto3.client('bedrock-data-automation')
    
    try:
        # Check if blueprint already exists
        list_response = bda_client.list_blueprints(blueprintStageFilter='ALL')
        existing_blueprint = next(
            (bp for bp in list_response['blueprints'] 
             if bp.get('blueprintName') == blueprint_name), 
            None
        )
        
        if existing_blueprint:
            print(f"Updating existing blueprint: {blueprint_name}")
            response = bda_client.update_blueprint(
                blueprintArn=existing_blueprint['blueprintArn'],
                blueprintStage=blueprint_stage,
                schema=json.dumps(blueprint_schema)
            )
        else:
            print(f"Creating new blueprint: {blueprint_name}")
            response = bda_client.create_blueprint(
                blueprintName=blueprint_name,
                type=blueprint_type,
                blueprintStage=blueprint_stage,
                schema=json.dumps(blueprint_schema)
            )
        
        return response['blueprint']['blueprintArn']
        
    except Exception as e:
        print(f"Error creating/updating blueprint: {e}")
        raise


def transform_custom_output(inference_result, explainability_info):
    """Transform custom output with confidence scores"""
    result = {"forms": {}, "tables": {}}
    
    def add_confidence(value, conf_info):
        if isinstance(conf_info, dict) and "confidence" in conf_info:
            return {"value": value, "confidence": conf_info["confidence"]}
        return value
    
    def process_list_item(item, conf_info):
        if isinstance(conf_info, dict):
            return {k: add_confidence(v, conf_info.get(k, {})) for k, v in item.items()}
        return item
    
    # Process the inference result
    for key, value in inference_result.items():
        confidence_data = explainability_info.get(key, {})
        
        if isinstance(value, list):
            # Handle lists (tables)
            processed_list = []
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    conf_info = confidence_data[idx] if isinstance(confidence_data, list) else confidence_data
                    processed_list.append(process_list_item(item, conf_info))
            result["tables"][key] = processed_list
        else:
            # Handle simple key-value pairs (forms)
            result["forms"][key] = add_confidence(value, confidence_data)
    
    return result


def restart_kernel():
    """Function to display message after restart"""
    # Wait for kernel restart
    time.sleep(2)
    print("Restarting Kernel...Wait a few seconds and progress executing subsequent cells.")


def wait_for_completion(
    client,
    get_status_function,
    status_kwargs,
    status_path_in_response,
    completion_states,
    error_states,
    max_iterations=60,
    delay=10
):
    """Generic function to wait for AWS operations to complete"""
    for _ in range(max_iterations):
        try:
            response = get_status_function(**status_kwargs)
            status = get_nested_value(response, status_path_in_response)

            if status in completion_states:
                print(f"Operation completed with status: {status}")
                return response

            if status in error_states:
                raise Exception(f"Operation failed with status: {status}")

            print(f"Current status: {status}. Waiting...")
            time.sleep(delay)

        except ClientError as e:
            raise Exception(f"Error checking status: {str(e)}")

    raise Exception(f"Operation timed out after {max_iterations} iterations")


def get_nested_value(data, path):
    """
    Retrieve a value from a nested dictionary using a dot-separated path.
    
    :param data: The dictionary to search
    :param path: A string representing the path to the value, e.g., "Job.Status"
    :return: The value at the specified path, or None if not found
    """
    keys = path.split('.')
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def preview_pdf_pages(pdf_path, page_range=None, width=600):
    """Convert multiple PDF pages to images for display in notebook
    
    Args:
        pdf_path: Path to the PDF file
        page_range: tuple (start, end) or list of page numbers, or None for first 3 pages
        width: Display width for images
    """
    try:
        with pymupdf.open(pdf_path) as doc:
            total_pages = len(doc)
            
            # Determine which pages to show
            if page_range is None:
                # Default: show first 3 pages
                pages_to_show = list(range(min(3, total_pages)))
            elif isinstance(page_range, tuple):
                # Range: (start, end)
                start, end = page_range
                pages_to_show = list(range(start, min(end, total_pages)))
            elif isinstance(page_range, list):
                # Specific page numbers
                pages_to_show = [p for p in page_range if p < total_pages]
            else:
                pages_to_show = [0]  # fallback to first page
            
            print(f"Showing {len(pages_to_show)} pages from PDF ({total_pages} total pages)")
            print("=" * 60)
            
            for page_num in pages_to_show:
                page = doc[page_num]
                
                # Convert to image
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                # Display page header and image
                print(f"\n📄 Page {page_num + 1}:")
                display(IPImage(data=img_data, width=width))
                
    except Exception as e:
        print(f"Could not preview PDF: {e}")
        print(f"PDF file location: {pdf_path}")
