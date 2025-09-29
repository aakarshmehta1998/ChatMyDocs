# s3_utils.py

import streamlit as st
import boto3
import os
import json
from botocore.exceptions import ClientError


def get_s3_client():
    """Initializes and returns a boto3 S3 client using credentials from st.secrets."""
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION"]
    )


def upload_file_to_s3(file_bytes, bucket_name, object_name):
    """Uploads file bytes to an S3 bucket."""
    s3_client = get_s3_client()
    try:
        s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=file_bytes)
        st.info(f"📄 Uploaded '{os.path.basename(object_name)}' to S3.")
        return True
    except ClientError as e:
        st.error(f"Error uploading to S3: {e}")
        return False


# --- NEW FUNCTIONS ---

def save_json_to_s3(data, bucket_name, object_name):
    """Saves a Python dictionary or list as a JSON file to S3."""
    s3_client = get_s3_client()
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=json.dumps(data, indent=4).encode('utf-8'),
            ContentType='application/json'
        )
        return True
    except ClientError as e:
        st.error(f"Error saving JSON to S3: {e}")
        return False


def load_json_from_s3(bucket_name, object_name):
    """Loads a JSON file from S3 and returns it as a Python object."""
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_name)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except ClientError as e:
        # If the file doesn't exist (e.g., new chat), it's not an error.
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        else:
            st.error(f"Error loading JSON from S3: {e}")
            return None


def list_folders_in_s3(bucket_name, prefix):
    """Lists 'subdirectories' (common prefixes) in an S3 bucket for a user."""
    s3_client = get_s3_client()
    # Ensure the prefix ends with a slash to properly list "directories"
    if not prefix.endswith('/'):
        prefix += '/'

    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    folders = []
    try:
        for page in pages:
            if "CommonPrefixes" in page:
                for obj in page['CommonPrefixes']:
                    # Extract folder name from prefix (e.g., 'user/kb_name/' -> 'kb_name')
                    folder_name = obj.get('Prefix').strip('/').split('/')[-1]
                    folders.append(folder_name)
        return folders
    except ClientError as e:
        st.error(f"Error listing knowledge bases from S3: {e}")
        return []


def delete_folder_from_s3(bucket_name, prefix):
    """Deletes all objects within a 'folder' in S3."""
    s3_client = get_s3_client()
    try:
        # List all objects with the given prefix
        objects_to_delete_response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        if 'Contents' in objects_to_delete_response:
            # Format the list for the delete_objects call
            delete_keys = {'Objects': [{'Key': obj['Key']} for obj in objects_to_delete_response['Contents']]}
            s3_client.delete_objects(Bucket=bucket_name, Delete=delete_keys)
        return True
    except ClientError as e:
        st.error(f"Error deleting knowledge base from S3: {e}")
        return False