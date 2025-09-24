# auth.py

import streamlit as st
import boto3
from botocore.exceptions import ClientError


def get_dynamodb_table():
    """Initializes and returns a boto3 DynamoDB table resource."""
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION"]
    )
    return dynamodb.Table('chatmydocs_users')


def load_credentials_from_db():
    """Loads all user credentials from the DynamoDB table."""
    table = get_dynamodb_table()
    try:
        response = table.scan()
        users = response.get('Items', [])

        credentials = {"usernames": {}}
        for user in users:
            username = user['username']
            credentials["usernames"][username] = {
                "email": user['email'],
                "name": user['name'],
                "password": user['password']
            }
        return credentials
    except ClientError as e:
        st.error(f"Failed to load credentials from DynamoDB: {e.response['Error']['Message']}")
        return {"usernames": {}}


def save_new_user_to_db(username, name, email, hashed_password):
    """Saves a new user's details to the DynamoDB table."""
    table = get_dynamodb_table()
    try:
        table.put_item(
            Item={
                'username': username,
                'name': name,
                'email': email,
                'password': hashed_password
            }
        )
        return True
    except ClientError as e:
        st.error(f"Failed to register user in DynamoDB: {e.response['Error']['Message']}")
        return False