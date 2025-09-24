import streamlit as st
import boto3
import os

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
        # Using a subtle info message to show progress
        st.info(f"📄 Uploaded '{os.path.basename(object_name)}' to S3.")
        return True
    except Exception as e:
        st.error(f"Error uploading to S3: {e}")
        return False