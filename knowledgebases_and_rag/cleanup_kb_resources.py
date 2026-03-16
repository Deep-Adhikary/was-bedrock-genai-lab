#!/usr/bin/env python3
"""
Cleanup script for Knowledge Base resources created in 01_create_ingest_documents_test_kb.ipynb

This script deletes:
- AOSS Knowledge Base and resources
- S3 Vectors Knowledge Base and resources
- S3 data source bucket
- IAM roles and policies
- Local data files

Usage:
    python cleanup_kb_resources.py [--dry-run] [--region REGION]

Options:
    --dry-run    Show what would be deleted without actually deleting
    --region     AWS region (default: us-east-1)
"""

import boto3
import json
import time
import os
import sys
import argparse
import shutil
from botocore.exceptions import ClientError


class KnowledgeBaseCleanup:
    def __init__(self, region_name='us-east-1', dry_run=False):
        self.region_name = region_name
        self.dry_run = dry_run
        
        # Initialize clients
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.aoss_client = boto3.client('opensearchserverless', region_name=region_name)
        self.s3vectors_client = boto3.client('s3vectors', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)
        self.sts_client = boto3.client('sts', region_name=region_name)
        
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        
        print(f"🔧 Initialized cleanup for region: {region_name}")
        print(f"📋 Account: {self.account_id}")
        if dry_run:
            print("🔍 DRY RUN MODE - No resources will be deleted")
        print()
    
    def safe_delete(self, delete_func, resource_name, *args, **kwargs):
        """Safely delete a resource with error handling"""
        if self.dry_run:
            print(f"[DRY RUN] Would delete {resource_name}")
            return True
        
        try:
            delete_func(*args, **kwargs)
            print(f"✅ Deleted {resource_name}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ResourceNotFoundException', 'NoSuchEntity', 'NoSuchBucket', 'NotFound']:
                print(f"ℹ️  {resource_name} not found (already deleted)")
            else:
                print(f"❌ Error deleting {resource_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error deleting {resource_name}: {e}")
            return False
    
    def wait_for_deletion(self, check_func, resource_name, max_wait=300, interval=5):
        """Wait for a resource to be deleted"""
        if self.dry_run:
            return True
        
        print(f"⏳ Waiting for {resource_name} deletion...", end="", flush=True)
        elapsed = 0
        while elapsed < max_wait:
            if not check_func():
                print(" Done!")
                return True
            print(".", end="", flush=True)
            time.sleep(interval)
            elapsed += interval
        print(" Timeout!")
        return False
    
    def find_knowledge_bases(self):
        """Find Knowledge Bases matching our pattern"""
        kb_ids = {'aoss': [], 's3vectors': []}
        
        try:
            paginator = self.bedrock_agent_client.get_paginator('list_knowledge_bases')
            for page in paginator.paginate():
                for kb in page.get('knowledgeBaseSummaries', []):
                    kb_name = kb['name']
                    kb_id = kb['knowledgeBaseId']
                    
                    if 'aoss' in kb_name.lower():
                        kb_ids['aoss'].append(kb_id)
                        print(f"Found AOSS KB: {kb_name} ({kb_id})")
                    elif 's3vectors' in kb_name.lower() or 's3-vectors' in kb_name.lower():
                        kb_ids['s3vectors'].append(kb_id)
                        print(f"Found S3 Vectors KB: {kb_name} ({kb_id})")
        except Exception as e:
            print(f"ℹ️  Could not list Knowledge Bases: {e}")
        
        return kb_ids
    
    def delete_knowledge_base(self, kb_id, kb_type):
        """Delete a Knowledge Base and its data sources"""
        print(f"\n🗑️  Deleting {kb_type} Knowledge Base: {kb_id}")
        
        # Delete data sources first
        try:
            ds_list = self.bedrock_agent_client.list_data_sources(knowledgeBaseId=kb_id)
            for ds in ds_list.get('dataSourceSummaries', []):
                self.safe_delete(
                    self.bedrock_agent_client.delete_data_source,
                    f"{kb_type} Data Source {ds['dataSourceId']}",
                    knowledgeBaseId=kb_id,
                    dataSourceId=ds['dataSourceId']
                )
        except Exception as e:
            print(f"ℹ️  Could not list/delete data sources: {e}")
        
        # Delete the Knowledge Base
        self.safe_delete(
            self.bedrock_agent_client.delete_knowledge_base,
            f"{kb_type} Knowledge Base {kb_id}",
            knowledgeBaseId=kb_id
        )
        
        if not self.dry_run:
            time.sleep(5)
    
    def delete_aoss_resources(self):
        """Delete OpenSearch Serverless resources"""
        print("\n" + "="*60)
        print("Deleting OpenSearch Serverless Resources")
        print("="*60)
        
        # Find and delete collections
        try:
            response = self.aoss_client.list_collections()
            for collection in response.get('collectionSummaries', []):
                collection_name = collection['name']
                if 'bedrock' in collection_name.lower() and 'rag' in collection_name.lower():
                    collection_id = collection['id']
                    print(f"\nFound AOSS collection: {collection_name}")
                    
                    self.safe_delete(
                        self.aoss_client.delete_collection,
                        f"AOSS Collection {collection_name}",
                        id=collection_id
                    )
                    
                    if not self.dry_run:
                        def check_collection_exists():
                            try:
                                resp = self.aoss_client.batch_get_collection(ids=[collection_id])
                                return len(resp.get('collectionDetails', [])) > 0
                            except:
                                return False
                        
                        self.wait_for_deletion(check_collection_exists, "AOSS Collection")
        except Exception as e:
            print(f"ℹ️  Could not list AOSS collections: {e}")
        
        # Delete security policies
        for policy_type in ['encryption', 'network']:
            try:
                response = self.aoss_client.list_security_policies(type=policy_type)
                for policy in response.get('securityPolicySummaries', []):
                    policy_name = policy['name']
                    if 'bedrock' in policy_name.lower():
                        self.safe_delete(
                            self.aoss_client.delete_security_policy,
                            f"{policy_type.title()} Policy {policy_name}",
                            name=policy_name,
                            type=policy_type
                        )
            except Exception as e:
                print(f"ℹ️  Could not list {policy_type} policies: {e}")
        
        # Delete access policies
        try:
            response = self.aoss_client.list_access_policies(type='data')
            for policy in response.get('accessPolicySummaries', []):
                policy_name = policy['name']
                if 'bedrock' in policy_name.lower():
                    self.safe_delete(
                        self.aoss_client.delete_access_policy,
                        f"Access Policy {policy_name}",
                        name=policy_name,
                        type='data'
                    )
        except Exception as e:
            print(f"ℹ️  Could not list access policies: {e}")
    
    def delete_s3vectors_resources(self):
        """Delete S3 Vectors resources"""
        print("\n" + "="*60)
        print("Deleting S3 Vectors Resources")
        print("="*60)
        
        try:
            response = self.s3vectors_client.list_vector_buckets()
            for bucket in response.get('vectorBuckets', []):
                bucket_name = bucket['vectorBucketName']
                if 'bedrock-kb-s3vectors' in bucket_name:
                    print(f"\nFound S3 Vectors bucket: {bucket_name}")
                    
                    # Delete indexes first
                    try:
                        indexes = self.s3vectors_client.list_indexes(vectorBucketName=bucket_name)
                        for idx in indexes.get('indexes', []):
                            self.safe_delete(
                                self.s3vectors_client.delete_index,
                                f"S3 Vectors Index {idx['indexName']}",
                                vectorBucketName=bucket_name,
                                indexName=idx['indexName']
                            )
                    except Exception as e:
                        print(f"ℹ️  Could not list indexes: {e}")
                    
                    if not self.dry_run:
                        time.sleep(5)
                    
                    # Delete the bucket
                    self.safe_delete(
                        self.s3vectors_client.delete_vector_bucket,
                        f"S3 Vectors Bucket {bucket_name}",
                        vectorBucketName=bucket_name
                    )
        except Exception as e:
            print(f"ℹ️  Could not list S3 Vectors buckets: {e}")
    
    def delete_s3_buckets(self):
        """Delete S3 data source buckets"""
        print("\n" + "="*60)
        print("Deleting S3 Data Source Buckets")
        print("="*60)
        
        try:
            response = self.s3_client.list_buckets()
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                if f'bedrock-kb-{self.region_name}-{self.account_id}' in bucket_name:
                    print(f"\nFound S3 bucket: {bucket_name}")
                    
                    # Delete all objects first
                    if not self.dry_run:
                        try:
                            obj_response = self.s3_client.list_objects_v2(Bucket=bucket_name)
                            if 'Contents' in obj_response:
                                objects = [{'Key': obj['Key']} for obj in obj_response['Contents']]
                                if objects:
                                    self.s3_client.delete_objects(
                                        Bucket=bucket_name,
                                        Delete={'Objects': objects}
                                    )
                                    print(f"  ✅ Deleted {len(objects)} objects")
                        except Exception as e:
                            print(f"  ℹ️  Could not delete objects: {e}")
                    
                    # Delete the bucket
                    self.safe_delete(
                        self.s3_client.delete_bucket,
                        f"S3 Bucket {bucket_name}",
                        Bucket=bucket_name
                    )
        except Exception as e:
            print(f"ℹ️  Could not list S3 buckets: {e}")
    
    def delete_iam_resources(self):
        """Delete IAM roles and policies"""
        print("\n" + "="*60)
        print("Deleting IAM Roles and Policies")
        print("="*60)
        
        try:
            paginator = self.iam_client.get_paginator('list_roles')
            for page in paginator.paginate():
                for role in page['Roles']:
                    role_name = role['RoleName']
                    if ('AmazonBedrockExecutionRoleForKnowledgeBase_' in role_name or
                        'AmazonBedrockExecutionRoleForS3Vectors_' in role_name):
                        print(f"\nFound role: {role_name}")
                        
                        # Detach and delete policies
                        if not self.dry_run:
                            try:
                                attached = self.iam_client.list_attached_role_policies(RoleName=role_name)
                                for policy in attached.get('AttachedPolicies', []):
                                    policy_arn = policy['PolicyArn']
                                    self.iam_client.detach_role_policy(
                                        RoleName=role_name,
                                        PolicyArn=policy_arn
                                    )
                                    print(f"  ✅ Detached {policy['PolicyName']}")
                                    
                                    # Delete custom policies
                                    if not policy_arn.startswith('arn:aws:iam::aws:'):
                                        self.safe_delete(
                                            self.iam_client.delete_policy,
                                            f"Policy {policy['PolicyName']}",
                                            PolicyArn=policy_arn
                                        )
                            except Exception as e:
                                print(f"  ℹ️  Could not detach policies: {e}")
                        
                        # Delete the role
                        self.safe_delete(
                            self.iam_client.delete_role,
                            f"IAM Role {role_name}",
                            RoleName=role_name
                        )
        except Exception as e:
            print(f"ℹ️  Could not list IAM roles: {e}")
    
    def delete_local_files(self):
        """Delete local data files"""
        print("\n" + "="*60)
        print("Deleting Local Files")
        print("="*60)
        
        data_dir = "./data"
        if os.path.exists(data_dir):
            if self.dry_run:
                print(f"[DRY RUN] Would delete directory: {data_dir}")
            else:
                try:
                    shutil.rmtree(data_dir)
                    print(f"✅ Deleted directory: {data_dir}")
                except Exception as e:
                    print(f"❌ Error deleting {data_dir}: {e}")
        else:
            print(f"ℹ️  Directory {data_dir} not found")
    
    def run_cleanup(self):
        """Run the complete cleanup process"""
        print("\n" + "="*60)
        print("KNOWLEDGE BASE CLEANUP")
        print("="*60)
        
        # Find Knowledge Bases
        kb_ids = self.find_knowledge_bases()
        
        # Delete Knowledge Bases
        for kb_id in kb_ids['aoss']:
            self.delete_knowledge_base(kb_id, 'AOSS')
        
        for kb_id in kb_ids['s3vectors']:
            self.delete_knowledge_base(kb_id, 'S3 Vectors')
        
        # Delete vector store resources
        self.delete_aoss_resources()
        self.delete_s3vectors_resources()
        
        # Delete S3 buckets
        self.delete_s3_buckets()
        
        # Delete IAM resources
        self.delete_iam_resources()
        
        # Delete local files
        self.delete_local_files()
        
        # Summary
        print("\n" + "="*60)
        print("CLEANUP COMPLETE")
        print("="*60)
        if self.dry_run:
            print("\n🔍 DRY RUN - No resources were actually deleted")
            print("Run without --dry-run to perform actual deletion")
        else:
            print("\n✅ All resources have been cleaned up!")
            print("\n⚠️  Note: Some resources may take a few minutes to fully delete.")


def main():
    parser = argparse.ArgumentParser(
        description='Cleanup Knowledge Base resources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--region',
        default=os.environ.get('AWS_REGION', 'us-east-1'),
        help='AWS region (default: us-east-1 or AWS_REGION env var)'
    )
    
    args = parser.parse_args()
    
    try:
        cleanup = KnowledgeBaseCleanup(region_name=args.region, dry_run=args.dry_run)
        cleanup.run_cleanup()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
