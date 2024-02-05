import json
from datetime import timedelta, datetime
from random import sample
from collections import defaultdict
import os
import openai
from openai import OpenAIError
import requests
import streamlit as st
import streamlit.components.v1 as components

# Define a function to get the user's access token
def refresh_token(refresh_token):
    refresh_response = requests.post(
        f'{os.getenv("DJANGO_URL")}/auth/api/token/refresh/', 
        json={'refresh': refresh_token}
    )
    print(f'refresh_response: {refresh_response}')
    return refresh_response.json() if refresh_response.status_code == 200 else None



# Use this in your API calls
def api_call_with_refresh(url, method='get', data=None, headers=None):
    response = requests.request(method, url, json=data, headers=headers)
    if response.status_code == 401:  # Token expired
        new_tokens = refresh_token(st.session_state.user_info["refresh"])
        if new_tokens:
            st.session_state.user_info.update(new_tokens)

            headers['Authorization'] = f'Bearer {new_tokens["access"]}'
            response = requests.request(method, url, json=data, headers=headers)  # Retry with new token
    return response

# Define a function to check if a user is authenticated
def is_user_authenticated():
    return 'user_info' in st.session_state and 'access' in st.session_state.user_info



