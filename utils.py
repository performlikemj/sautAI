import json
from datetime import timedelta, datetime
from random import sample
from collections import defaultdict
import os
import openai
from openai import OpenAIError
import requests
import streamlit as st
from extra_streamlit_components import CookieManager

# Assuming you have already initialized the CookieManager
cookies_manager = CookieManager()

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

            # Update the cookie with the new access token
            cookies_manager.set("access_token", val=new_tokens["access"], max_age=86400)

            headers['Authorization'] = f'Bearer {new_tokens["access"]}'
            response = requests.request(method, url, json=data, headers=headers)  # Retry with new token
    return response

# Define a function to check if a user is authenticated
def is_user_authenticated():
    return 'user_info' in st.session_state and 'access' in st.session_state.user_info
