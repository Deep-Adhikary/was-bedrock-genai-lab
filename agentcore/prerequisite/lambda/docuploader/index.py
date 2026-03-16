import boto3
import cfnresponse
import os
import glob

def lambda_handler(event, context):
    """
    Custom resource Lambda function to upload documentation files to S3.
    This function reads documentation files from the docs/ directory
    within the Lambda deployment package and uploads them to S3.
    """
    bucket_name = event['ResourceProperties']['BucketName']
    s3_client = boto3.client('s3')
    
    try:
        if event['RequestType'] == 'Delete':
            # Empty the S3 bucket on stack deletion
            
            try:
                # Delete all objects in the bucket
                paginator = s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name):
                    if 'Contents' in page:
                        objects = [{'Key': obj['Key']} for obj in page['Contents']]
                        s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': objects}
                        )
                        print(f"Deleted {len(objects)} objects from bucket {bucket_name}")
                
            except Exception as e:
                # Don't fail the stack deletion if cleanup fails
                print(f"Error during bucket cleanup: {str(e)}")
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

        else:
    
            # Get the directory where this Lambda function is located
            lambda_dir = os.path.dirname(os.path.abspath(__file__))
            docs_dir = os.path.join(lambda_dir, 'docs')
            
            uploaded_count = 0
            
            # Read all .txt files from the docs directory
            doc_files = glob.glob(os.path.join(docs_dir, '*.txt'))
            
            for file_path in doc_files:
                filename = os.path.basename(file_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=filename,
                        Body=content.encode('utf-8'),
                        ContentType='text/plain'
                    )
                    uploaded_count += 1
                    print(f"Uploaded {filename}")
                except Exception as e:
                    print(f"Failed to upload {filename}: {str(e)}")
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'FilesUploaded': uploaded_count
            })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})