import json
import uuid
from random import sample
from collections import defaultdict
import os
import time
from typing_extensions import override
from typing import Tuple, Iterator, Optional, Any
from openai import OpenAIError
from openai import AssistantEventHandler, OpenAI, BadRequestError
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Text, TextDelta
import requests
import streamlit as st
import logging
from dotenv import load_dotenv
import re
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

# Retrieve the environment variable in Python
django_url = os.getenv("DJANGO_URL")

openai_env_key = os.getenv("OPENAI_KEY")

# ============================
# Utility Functions for Error Handling
# ============================
#
# USAGE EXAMPLES:
#
# 1. Safe dictionary access:
#    value = safe_get(data, 'key', 'default_value')
#    nested_value = safe_get_nested(data, ['level1', 'level2', 'key'], 'default')
#
# 2. Function decorator for error handling:
#    @handle_api_errors
#    def my_api_function():
#        # Your API code here
#        return response.json()['data']['value']  # Will be safely handled
#
# 3. Safe JSON parsing:
#    data = safe_json_loads(json_string, default={})
#
# These utilities prevent crashes from KeyError, IndexError, and other common exceptions
# while providing useful logging and user-friendly error messages.
# ============================

def safe_get_nested(data, keys, default=None, log_errors=True):
    """
    Safely access nested dictionary/list values with error handling.
    
    Args:
        data: The data structure to access (dict, list, etc.)
        keys: A list of keys/indices to access (e.g., ['key1', 'key2', 0])
        default: Default value to return if access fails
        log_errors: Whether to log errors when keys are not found
    
    Returns:
        The value at the nested location, or default if not found
    
    Examples:
        safe_get_nested({'a': {'b': 'value'}}, ['a', 'b']) -> 'value'
        safe_get_nested({'a': [{'b': 'value'}]}, ['a', 0, 'b']) -> 'value'
        safe_get_nested({'a': {}}, ['a', 'missing'], 'default') -> 'default'
    """
    try:
        current = data
        key_path = []
        
        for key in keys:
            key_path.append(str(key))
            
            if isinstance(current, dict):
                if key not in current:
                    if log_errors:
                        logging.warning(f"Key '{key}' not found in dict at path: {' -> '.join(key_path)}. Available keys: {list(current.keys())}")
                    return default
                current = current[key]
            elif isinstance(current, list):
                try:
                    index = int(key)
                    if index >= len(current) or index < -len(current):
                        if log_errors:
                            logging.warning(f"Index {index} out of range for list of length {len(current)} at path: {' -> '.join(key_path)}")
                        return default
                    current = current[index]
                except (ValueError, TypeError):
                    if log_errors:
                        logging.warning(f"Invalid list index '{key}' at path: {' -> '.join(key_path)}")
                    return default
            else:
                if log_errors:
                    logging.warning(f"Cannot access key '{key}' on {type(current)} at path: {' -> '.join(key_path)}")
                return default
        
        return current
        
    except Exception as e:
        if log_errors:
            logging.error(f"Error accessing nested data with keys {keys}: {str(e)}")
            logging.error(f"Data structure: {type(data)} - {data}")
        return default

def safe_get(data, key, default=None, log_errors=True):
    """
    Safely get a value from a dictionary with error handling.
    
    Args:
        data: The dictionary to access
        key: The key to access
        default: Default value to return if key is not found
        log_errors: Whether to log errors when key is not found
    
    Returns:
        The value at the key, or default if not found
    """
    try:
        if not isinstance(data, dict):
            if log_errors:
                logging.warning(f"Expected dict but got {type(data)} when accessing key '{key}'")
            return default
        
        if key not in data:
            if log_errors:
                logging.warning(f"Key '{key}' not found in dict. Available keys: {list(data.keys())}")
            return default
            
        return data[key]
        
    except Exception as e:
        if log_errors:
            logging.error(f"Error accessing key '{key}': {str(e)}")
        return default

def handle_api_errors(func):
    """
    Decorator to handle common API errors and provide user-friendly messages.
    
    Usage:
        @handle_api_errors
        def my_function():
            # Your function code here
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError as e:
            error_msg = f"Missing expected data field: {str(e)}"
            logging.error(f"KeyError in {func.__name__}: {error_msg}")
            logging.error(traceback.format_exc())
            st.error("We're experiencing a data formatting issue. Please try again or contact support if the issue persists.")
            return None
        except requests.exceptions.ConnectionError:
            error_msg = "Unable to connect to the server"
            logging.error(f"Connection error in {func.__name__}: {error_msg}")
            st.error("Unable to connect to the server. Please check your internet connection and try again.")
            return None
        except requests.exceptions.Timeout:
            error_msg = "Request timed out"
            logging.error(f"Timeout error in {func.__name__}: {error_msg}")
            st.error("The request is taking too long. Please try again.")
            return None
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error: {str(e)}"
            logging.error(f"HTTP error in {func.__name__}: {error_msg}")
            st.error("Server returned an error. Please try again later.")
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(f"Unexpected error in {func.__name__}: {error_msg}")
            logging.error(traceback.format_exc())
            st.error("An unexpected error occurred. Our team has been notified.")
            return None
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def safe_json_loads(json_string, default=None, log_errors=True):
    """
    Safely parse JSON string with error handling.
    
    Args:
        json_string: The JSON string to parse
        default: Default value to return if parsing fails
        log_errors: Whether to log errors when parsing fails
    
    Returns:
        The parsed JSON object, or default if parsing fails
    """
    try:
        if not json_string:
            return default
        
        return json.loads(json_string)
        
    except json.JSONDecodeError as e:
        if log_errors:
            logging.error(f"JSON parsing error: {str(e)}")
            logging.error(f"JSON string: {json_string}")
        return default
    except Exception as e:
        if log_errors:
            logging.error(f"Unexpected error parsing JSON: {str(e)}")
        return default

# ============================
# API Related Functions
# ============================

def fetch_languages():
    """
    Fetch available languages from the API endpoint.
    Returns a list of language objects with code, name, name_local, and bidi properties.
    Falls back to default languages if API call fails.
    """
    try:
        api_url = f"{os.getenv('DJANGO_URL')}/auth/api/languages/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            # Fallback to default languages if API call fails
            return [
                {"code": "en", "name": "English", "name_local": "English", "bidi": False},
                {"code": "jp", "name": "Japanese", "name_local": "日本語", "bidi": False},
                {"code": "es", "name": "Spanish", "name_local": "Español", "bidi": False},
                {"code": "fr", "name": "French", "name_local": "Français", "bidi": False}
            ]
    except Exception as e:
        logging.error(f"Error fetching languages: {e}")
        # Fallback to default languages if API call fails
        return [
            {"code": "en", "name": "English", "name_local": "English", "bidi": False},
            {"code": "jp", "name": "Japanese", "name_local": "日本語", "bidi": False},
            {"code": "es", "name": "Spanish", "name_local": "Español", "bidi": False},
            {"code": "fr", "name": "French", "name_local": "Français", "bidi": False}
        ]

# ============================
# HTTP Session Management
# ============================
def get_api_session() -> requests.Session:
    """
    Return a per-tab requests.Session() whose cookies persist across reruns.
    """
    if "api_session" not in st.session_state:
        sess = requests.Session()
        sess.headers.update({"User-Agent": "sautAI-frontend/1.0"})
        st.session_state["api_session"] = sess
    return st.session_state["api_session"]

def dj_request(method: str, path: str, **kw):
    """Make a request to Django backend using the persistent session"""
    full_url = f"{django_url}{path}"
    return get_api_session().request(method.upper(), full_url, **kw)

# convenience shorthands
def dj_get(path, **kw):  return dj_request("GET", path, **kw)
def dj_post(path, **kw): return dj_request("POST", path, **kw)
def dj_put(path, **kw):  return dj_request("PUT", path, **kw)
def dj_delete(path, **kw): return dj_request("DELETE", path, **kw)

client = OpenAI(api_key=openai_env_key)

openai_headers = {
    "Content-Type": "application/json",
    "OpenAI-Beta": "assistants=v2",
}


# ============================
# Responses API EventHandler
# ============================
class ResponsesEventHandler:
    """
    Event handler for OpenAI Responses API streaming.
    This class mimics the interface of the AssistantEventHandler to minimize code changes.
    """
    def __init__(self, placeholder=None):
        self.placeholder = placeholder
        self.full_response = ""
        self.tool_calls = []
        self.response_id = None
        self.done = False
        self.error = None
    
    def on_event(self, event):
        """Process events from the Responses API stream"""
        # TODO: Remove argument from on_event and use a spinner to show the tool call is happening
        try:
            # Handle different event types
            if hasattr(event, 'type'):
                # Handle response creation
                if event.type == 'response.created':
                    self.response_id = event.id if hasattr(event, 'id') else None
                
                # Handle text delta events
                elif event.type == 'response.output_text.delta':
                    # New SDK returns plain dict; use ['text'] accessor
                    text_piece = (
                        event.delta.text
                        if hasattr(event.delta, 'text')
                        else event.delta.get('text', '')
                    )
                    self.full_response += text_piece
                    if self.placeholder:
                        self.placeholder.markdown(self.full_response)
                
                # Handle function call events
                elif event.type == 'response.function_call.arguments.delta':
                    # Track function calls if needed
                    if hasattr(event, 'content') and isinstance(event.content, dict):
                        function_name = event.content.get('function', {}).get('name', '')
                        if function_name and self.placeholder:
                            self.placeholder.info(f"Calling tool: {function_name}")
                
                # Handle completion event
                elif event.type == 'response.completed':
                    self.done = True
                    if hasattr(event, 'content') and event.content:
                        self.full_response = event.content
                        if self.placeholder:
                            self.placeholder.markdown(self.full_response)
                
                # Handle error events
                elif event.type == 'error':
                    self.error = event.message if hasattr(event, 'message') else "Unknown error"
                    logging.error(f"Streaming error: {self.error}")
                    if self.placeholder:
                        self.placeholder.error(self.error)
        except Exception as e:
            logging.error(f"Error in ResponsesEventHandler: {str(e)}")
            self.error = str(e)
            if self.placeholder:
                self.placeholder.error(f"Error processing response: {str(e)}")
    
    def get_final_response(self):
        """Get the final response text"""
        return self.full_response
    
    def get_response_id(self):
        """Get the response ID for continuing the conversation"""
        return self.response_id

# ============================
# Streaming Functions
# ============================
# Helper function to stream text word by word
def yield_words(text: str) -> Iterator[str]:
    words = text.split(' ')
    for word in words:
        if word == '\n':
            yield word
            time.sleep(0.05)  # small pause for newline
        else:
            yield word + ' '
            time.sleep(0.05)  # small pause between words

def stream_response_generator(message: str, thread_id: str = None, is_guest: bool = False) -> Iterator[str]:
    """
    Generator function that streams a response from the backend using Server-Sent Events.
    """
    data = {'message': message}
    if thread_id:
        data['response_id'] = thread_id

    # Determine endpoint and headers
    if not is_guest and is_user_authenticated():
        # Add more detailed authentication logging
        # Add user_id to the payload for better backend identification
        data['user_id'] = st.session_state.get('user_id')
        path = '/customer_dashboard/api/assistant/stream-message/'
        headers = {'Authorization': f'Bearer {st.session_state.user_info.get("access")}'}
    else:
        path = '/customer_dashboard/api/assistant/guest-stream-message/'
        headers = {}

    # Mapping from internal tool names to user-friendly spinner text
    TOOL_NAME_MAP = {
        "update_chef_meal_order": "Updating your chef meal order",
        "generate_payment_link": "Generating a payment link",
        "determine_items_to_replenish": "Determining items to replenish",
        "set_emergency_supply_goal": "Setting your emergency supply goal",
        "get_user_summary": "Getting your health summary",
        "create_meal_plan": "Creating your meal plan",
        "modify_meal_plan": "Modifying your meal plan",
        "get_meal_plan": "Fetching your meal plan",
        "email_generate_meal_instructions": "Generating meal instructions for email",
        "stream_meal_instructions": "Streaming meal instructions",
        "stream_bulk_prep_instructions": "Streaming bulk prep instructions",
        "get_meal_plan_meals_info": "Getting meal plan's meal information",
        "find_related_youtube_videos": "Finding related YouTube videos",
        "get_meal_macro_info": "Getting meal macro information",
        "update_user_settings": "Updating your user settings",
        "get_user_settings": "Getting your user settings",
        "get_user_info": "Getting your user information",
        "get_current_date": "Checking the current date",
        "list_upcoming_meals": "Finding your upcoming meals",
        "find_nearby_supermarkets": "Finding nearby supermarkets",
        "check_pantry_items": "Checking your pantry items",
        "add_pantry_item": "Adding item to your pantry",
        "list_upcoming_meals": "Finding your upcoming meals",
        "list_dietary_preferences": "Checking all of sautAI's dietary preferences",
        "check_allergy_alert": "Checking for possible allergens",
        "suggest_alternatives": "Suggesting alternatives meals",
        "get_expiring_items": "Finding expiring items",
        "generate_shopping_list": "Generating your shopping list",
        "find_local_chefs": "Finding local chefs",
        "get_chef_details": "Getting chef details",
        "view_chef_meals": "Viewing chef meals",
        "place_chef_meal_order": "Placing your chef meal order",
        "get_order_details": "Getting order details",
        "cancel_order": "Cancelling your order",
        "create_payment_link": "Creating payment link",
        "check_payment_status": "Checking payment status",
        "process_refund": "Processing refund",
        "manage_dietary_preferences": "Managing dietary preferences",
        "check_meal_compatibility": "Checking meal compatibility",
        "suggest_alternatives": "Suggesting alternatives",
        "check_allergy_alert": "Checking for allergy alerts",
        "adjust_week_shift": "Adjusting the week view",
        "reset_current_week": "Resetting the week view",
        "update_goal": "Updating your goal",
        "get_goal": "Getting your goal information",
        "access_past_orders": "Accessing past orders",
        "guest_search_dishes": "Searching for dishes",
        "guest_search_chefs": "Searching for chefs",
        "guest_get_meal_plan": "Getting meal plan information",
        "guest_search_ingredients": "Searching ingredients",
        "chef_service_areas": "Checking chef service areas"
    }

    try:
        # Use our session-aware request helper to maintain cookies across requests
        with dj_post(path, json=data, headers=headers, stream=True) as response:
            status = getattr(response, 'status_code', None)
            if status != 200:
                error_message = f"Error: {status}" if status else "Failed to connect to server"
                yield error_message
                return

            accumulated_text = ""
            response_id = None
            spinner = None
            tool_call_in_progress = False # Flag to track tool call state

            # === Revised SSE loop ===
            # === SSE loop (clean, unified) ==================================
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue

                decoded = raw_line.decode("utf-8")
                if not decoded.startswith("data:"):
                    continue                                    # ignore keep‑alives

                payload = decoded[len("data:"):].strip()
                try:
                    sse_json = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                event_type = sse_json.get("type")

                # ── 1) conversation/turn created ────────────────────────────
                if event_type == "response.created" and "id" in sse_json:
                    response_id = sse_json["id"]
                    st.session_state["response_id"] = response_id
                    continue

                # ── 1.5) tool call begins → open spinner  ───────────────────
                TOOL_CALL_EVENTS = {
                    "response.tool",              # legacy
                    "response.function_call",     # new Responses API
                    "response.function_call.arguments.delta"
                }

                if event_type in TOOL_CALL_EVENTS:
                    if "name" in sse_json:
                        fn_name = sse_json["name"]
                        friendly = TOOL_NAME_MAP.get(fn_name, fn_name.replace("_", " ").title())
                        # … start spinner …
                    else:
                        # no tool name here; skip
                        continue
                    if spinner:
                        spinner.__exit__(None, None, None)
                    spinner = st.spinner(f"Calling tool: {friendly}…")
                    spinner.__enter__()
                    tool_call_in_progress = True
                    continue

                # ── 1.6) tool result arrives (we keep spinner until text) ───
                if event_type == "tool_result":
                    # You might display result cards here if desired
                    continue

                # ── 2) stream assistant text (both styles)  ─────────────────
                if event_type in ("text", "response.output_text.delta"):
                    if tool_call_in_progress and spinner:
                        spinner.__exit__(None, None, None)
                        spinner = None
                        tool_call_in_progress = False

                    delta_text = (
                        sse_json.get("content")              # backend "text"
                        or sse_json.get("delta", {}).get("text", "")  # legacy format
                    )
                    # de‑duplicate identical trailing chunks
                    if delta_text and not accumulated_text.endswith(delta_text):
                        accumulated_text += delta_text
                        yield delta_text
                    continue

                # ── 3) assistant turn finished ──────────────────────────────
                if event_type == "response.completed":
                    response_id = sse_json.get("id") or sse_json.get("response",{}).get("id")
                    break                                   # exit SSE loop

            # === loop ended – tidy up =======================================
            if spinner:
                spinner.__exit__(None, None, None)

            st.session_state["last_response_text"] = accumulated_text

    except requests.exceptions.RequestException as e:
        if spinner:
            spinner.__exit__(None, None, None)
        yield f"Connection error: {e}"
    except Exception as e:
        if spinner:
            spinner.__exit__(None, None, None)
        yield f"Unexpected error: {e}"

def display_streaming_response(message: str, thread_id: str = None, is_guest: bool = False) -> Tuple[str, str]:
    """
    Display a streaming response in Streamlit using st.write_stream.
    """
    try:
        # Render the stream
        st.write_stream(stream_response_generator(message, thread_id, is_guest))
        # Retrieve the ID (new or existing) and full text
        response_id = st.session_state.get('response_id', thread_id)
        full_response = st.session_state.get('last_response_text', "")
        return response_id, full_response
    except Exception as e:
        st.error(f"An error occurred: {e}")
        # On error, preserve thread_id
        return thread_id, f"Error: {e}"

def process_user_input(prompt, chat_container):
    """
    Process user input and display the streaming response.
    
    Args:
        prompt: The user message
        chat_container: The Streamlit container for displaying chat messages
    """
    # Add user message to chat history and display it
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with chat_container.chat_message("user"):
        st.markdown(prompt)
    
    # Determine if user is authenticated or a guest
    is_guest = not is_user_authenticated()
    # Get user_id if authenticated
    user_id = None if is_guest else st.session_state.get('user_id')
    
    # Display the assistant response with streaming
    with chat_container.chat_message("assistant"):
        try:
            # Use the updated display_streaming_response function that returns both response_id and full_response
            response_id, full_response = display_streaming_response(
                message=prompt,
                thread_id=st.session_state.get('thread_id'),
                is_guest=is_guest
            )
            
            # Update the thread ID in session state for conversation continuity
            if response_id:
                st.session_state.thread_id = response_id
            
            # Add the full response to chat history
            # This uses the actual response text instead of a placeholder
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": full_response
            })

            # --- Detect & render HTML payment button ------------------------
            parsed = None
            if isinstance(full_response, dict):
                parsed = full_response
            else:
                try:
                    parsed = json.loads(full_response)
                except (TypeError, ValueError):
                    pass

            if parsed and isinstance(parsed, dict) and parsed.get("html_button"):
                # Render the checkout button inside the current chat bubble
                st.markdown(parsed["html_button"], unsafe_allow_html=True)

            # Fetch follow-up recommendations if needed
            if not is_guest:
                fetch_follow_up_recommendations(st.session_state.thread_id)

        except Exception as e:
            logging.error(f"Error in process_user_input: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
            
            # Even in case of error, add an error message to chat history
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": f"Error: {str(e)}"
            })


# ============================
# Chat Functions
# ============================
def chat_with_gpt(message, thread_id=None, user_id=None):
    """
    Send a message to the GPT assistant and get a response.
    
    Args:
        message: The message to send
        thread_id: The thread ID (which is actually the response ID)
        user_id: The user ID (for authenticated users)
        
    Returns:
        A dictionary containing the response data
    """
    try:
        # Prepare the request data
        data = {
            'message': message
        }
        
        if thread_id:
            data['thread_id'] = thread_id
            
        if user_id:
            data['user_id'] = user_id
        
        # Make the API call
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f'{django_url}/customer_dashboard/api/chat_with_gpt/',
            method='post',
            data=data,
            headers=headers
        )
        if response and response.status_code == 200:
            return response.json()
        else:
            error_message = "Failed to get response from assistant."
            if response:
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_message = error_data['error']
                except:
                    pass
            logging.error(error_message)
            return None
    except Exception as e:
        logging.error(f"Error in chat_with_gpt: {e}")
        return None

def guest_chat_with_gpt(message, thread_id=None):
    """
    Send a message to the GPT assistant as a guest and get a response.
    
    Args:
        message: The message to send
        thread_id: The thread ID (which is actually the response ID)
        
    Returns:
        A dictionary containing the response data
    """
    try:
        # Prepare the request data
        data = {
            'message': message
        }
        
        if thread_id:
            data['thread_id'] = thread_id
            
        # Make the API call using our session-aware request helper
        response = dj_post(
            '/customer_dashboard/api/guest_chat_with_gpt/',
            json=data
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_message = "Failed to get response from assistant."
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_message = error_data['error']
            except:
                pass
            logging.error(error_message)
            return None
    except Exception as e:
        logging.error(f"Error in guest_chat_with_gpt: {e}")
        return None

def validate_input(input_value, input_type):
    """ Validate input based on the expected type """
    try:
        """ Validate input based on the expected type """
        if input_type == 'username':
            if not re.match("^[a-zA-Z0-9_.-]+$", input_value) or len(input_value) < 3:
                return False, "Username must be at least 3 characters long and contain only letters, numbers, underscores, or periods."
        elif input_type == 'email':
            if not re.match(r"[^@]+@[^@]+\.[^@]+", input_value):
                return False, "Invalid email format."
        elif input_type == 'password':
            if len(input_value) < 8 or not re.search(r"[A-Za-z]", input_value) or not re.search(r"[0-9]", input_value) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", input_value):
                return False, "Password must be at least 8 characters long, include a number, a letter, and a special character."
        elif input_type == 'phone_number':
            # Corrected regex for phone number formats
            if input_value and not re.match(r"^\+?(\d[\d().\s-]{7,}\d)$", input_value):
                return False, "Invalid phone number format. Accepts formats like +1234567890, (123) 456-7890, or 123-456-7890."
        elif input_type == 'postal_code':
            if input_value and len(input_value) < 3:  # Example validation, you may want to tailor this to specific country formats
                return False, "Postal code is too short."
        return True, ""
    except ValueError as ve:
        st.error(str(ve))
        return False

def parse_comma_separated_input(input_str):
    """
    Parses a comma-separated string into a list of trimmed strings.
    Removes any empty entries.
    
    Args:
        input_str (str): The input string containing comma-separated values.
    
    Returns:
        List[str]: A list of non-empty, trimmed strings.
    """
    return [pref.strip() for pref in input_str.split(',') if pref.strip()]

def footer():
    st.write("---")
    st.markdown(
        """
        <small style="color: #777;">
        <strong>Disclaimer:</strong> SautAI uses generative AI for its meal planning 
        and suggestions, which may occasionally produce incorrect or incomplete results. 
        Please verify any critical information and use caution.
        </small>
        """,
        unsafe_allow_html=True
    )

def refresh_chef_status():
    """
    Refresh the chef status from the backend to ensure session state is up to date.
    This should be called when there might be changes to chef status.
    """
    try:
        logging.warning("refresh_chef_status: Starting chef status refresh")
        if is_user_authenticated():
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            
            # Fetch latest user details
            user_response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', 
                method='get', 
                headers=headers
            )
            
            if user_response and user_response.status_code == 200:
                user_data = user_response.json()
                logging.warning(f"refresh_chef_status: Backend says is_chef={user_data.get('is_chef')}, current_role={user_data.get('current_role')}")
                
                # Update session state
                old_is_chef = st.session_state.get('is_chef', False)
                new_is_chef = user_data.get('is_chef', False)
                
                st.session_state['is_chef'] = new_is_chef
                st.session_state['current_role'] = user_data.get('current_role', 'customer')
                
                # Also update user_info if it exists
                if 'user_info' in st.session_state:
                    st.session_state['user_info']['is_chef'] = new_is_chef
                    st.session_state['user_info']['current_role'] = user_data.get('current_role', 'customer')
                
                # Return True if chef status changed
                status_changed = old_is_chef != new_is_chef
                logging.warning(f"refresh_chef_status: Status changed from {old_is_chef} to {new_is_chef}: {status_changed}")
                return status_changed
            else:
                logging.error(f"refresh_chef_status: API call failed. Status: {user_response.status_code if user_response else 'No response'}")
                return False
        else:
            logging.warning("refresh_chef_status: User not authenticated, skipping refresh")
            return False
    except Exception as e:
        logging.error(f"refresh_chef_status: Exception occurred: {str(e)}")
        return False

def display_chef_toggle_in_sidebar():
    """
    Displays a toggle in the sidebar for users with chef privileges to switch between chef and customer modes.
    This function should be called from the main app file to make the toggle available on all pages.
    """
    # Log the current session state for debugging
    logging.warning(f"Chef toggle check: is_chef={st.session_state.get('is_chef', 'NOT_SET')}, current_role={st.session_state.get('current_role', 'NOT_SET')}, is_logged_in={st.session_state.get('is_logged_in', 'NOT_SET')}")
    
    # Only show for users with chef privileges
    if 'is_chef' in st.session_state and st.session_state['is_chef']:
        logging.warning("Chef toggle: Displaying toggle - user has chef privileges")
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Chef Access")
        
        current_role = st.session_state.get('current_role', 'customer')
        is_chef_mode = st.sidebar.toggle(
            "Enable Chef Mode", 
            value=(current_role == 'chef'),
            help="Switch between chef and customer views"
        )
        
        # Handle toggle state change
        new_role = 'chef' if is_chef_mode else 'customer'
        
        if current_role != new_role:
            try:
                # Call API to update backend
                headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                response = api_call_with_refresh(
                    url=f"{os.getenv('DJANGO_URL')}/auth/api/switch_role/",
                    method='post',
                    headers=headers,
                    data={'role': new_role}
                )
                
                if response and response.status_code == 200:
                    # Update session state
                    st.session_state['current_role'] = new_role
                    st.sidebar.success(f"Switched to {new_role} mode!")
                    # If in chef mode, suggest navigating to chef meals page
                    if new_role == 'chef':
                        st.sidebar.info("You can now access the Chef Meals page.")
                    st.rerun()
                else:
                    st.sidebar.error(f"Failed to switch to {new_role} mode.")
                    logging.error(f"Failed to switch role. Status: {response.status_code if response else 'No response'}")
            except Exception as e:
                st.sidebar.error(f"Error switching modes: {str(e)}")
                logging.error(f"Error switching modes: {str(e)}")
                logging.error(traceback.format_exc())
    else:
        logging.warning("Chef toggle: NOT displaying - user does not have chef privileges or not logged in")
        # Check if user might be a chef but session state is outdated
        # Only do this check periodically to avoid excessive API calls
        if (is_user_authenticated() and 
            'last_chef_status_check' not in st.session_state or 
            time.time() - st.session_state.get('last_chef_status_check', 0) > 300):  # Check every 5 minutes
            
            logging.warning("Chef toggle: Performing periodic chef status refresh")
            # Refresh chef status from backend
            if refresh_chef_status():
                # Chef status changed, rerun to show the toggle
                st.session_state['last_chef_status_check'] = time.time()
                logging.warning("Chef toggle: Status changed, rerunning app")
                st.rerun()
            else:
                st.session_state['last_chef_status_check'] = time.time()
                logging.warning("Chef toggle: No status change detected")

def get_chef_meals_by_postal_code(meal_type=None, date=None, week_start_date=None, chef_id=None, include_compatible_only=False, page=1, page_size=10):
    """
    Fetch chef-created meals available for the user's postal code.
    
    Args:
        meal_type (str, optional): Filter by meal type (Breakfast, Lunch, Dinner)
        date (str, optional): Filter by specific date in YYYY-MM-DD format (backward compatibility)
        week_start_date (str, optional): Start date of the week in YYYY-MM-DD format
        chef_id (int, optional): Filter by specific chef ID
        include_compatible_only (bool, optional): Only return meals compatible with user's dietary preferences
        page (int, optional): Page number for pagination
        page_size (int, optional): Number of items per page
        
    Returns:
        dict: JSON response with chef meals data or None if the request failed
    """
    try:
        if not is_user_authenticated():
            st.error("You must be logged in to view chef meals.")
            return None
            
        # Build query parameters
        params = {'page': page, 'page_size': page_size}
        
        # Priority: week_start_date > date
        if week_start_date:
            params['week_start_date'] = week_start_date
        elif date:
            params['date'] = date
            
        if meal_type:
            params['meal_type'] = meal_type
        if chef_id:
            params['chef_id'] = chef_id
        if include_compatible_only:
            params['include_compatible_only'] = 'true'
            
        # Make authenticated API call
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/chef-meals-by-postal-code/',
            method='get',
            headers=headers,
            params=params
        )
        
        if response and response.status_code == 200:
            return response.json()
        elif response and response.status_code == 400:
            data = response.json()
            if data.get('code') == 'missing_postal_code':
                st.warning("Please set your postal code in your profile to see available chef meals.")
            return None
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching chef meals: {e}")
        st.error("Failed to load chef meals. Please try again later.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_chef_meals_by_postal_code: {e}")
        st.error("An unexpected error occurred while fetching chef meals.")
        return None

def replace_meal_with_chef_meal(meal_plan_meal_id, chef_meal_id, event_id=None, quantity=1, special_requests=None):
    """
    Replace a meal in the user's meal plan with a chef-created meal.
    
    Args:
        meal_plan_meal_id (int): ID of the meal plan meal to replace
        chef_meal_id (int): ID of the chef meal to use as replacement
        event_id (int, optional): ID of the specific chef meal event to use
        quantity (int, optional): Number of meals to order. Defaults to 1.
        special_requests (str, optional): Any special instructions for the chef
        
    Returns:
        dict: Response data containing status and message or None if failed
    """
    try:
        if not is_user_authenticated():
            st.error("You must be logged in to replace meals.")
            return None
            
        # Convert NumPy types to native Python types to ensure JSON serialization works
        meal_plan_meal_id = int(meal_plan_meal_id)
        chef_meal_id = int(chef_meal_id)
        quantity = int(quantity)
        if event_id is not None:
            event_id = int(event_id)
            
        # Prepare the payload
        payload = {
            'meal_plan_meal_id': meal_plan_meal_id,
            'chef_meal_id': chef_meal_id,
            'quantity': quantity
        }
        
        if event_id:
            payload['event_id'] = event_id
            
        if special_requests:
            payload['special_requests'] = special_requests
            

        # Make authenticated API call
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/replace_meal_plan_meal/',
            method='put',
            headers=headers,
            data=payload
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            error_message = "Failed to replace meal."
            if response and hasattr(response, 'json'):
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_message)
                except:
                    pass
            st.error(error_message)
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error replacing meal with chef meal: {e}")
        st.error("Failed to replace meal. Please try again later.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in replace_meal_with_chef_meal: {e}")
        st.error("An unexpected error occurred while replacing the meal.")
        return None
    
# Helper function to process streaming response
def process_streaming_response(stream_generator, st_container) -> str:
    """
    Process a streaming response and display it in a Streamlit container.
    
    Args:
        stream_generator: The generator yielding stream chunks
        st_container: The Streamlit container to display the response in
        
    Returns:
        The full response text
    """
    full_response = ""
    placeholder = st_container.empty()
    
    try:
        for chunk in stream_generator:
            if 'error' in chunk:
                st_container.error(chunk['error'])
                continue
                
            # Handle different event types based on the OpenAI documentation
            if 'type' in chunk:
                # Handle response.created event
                if chunk['type'] == 'response.created':
                    st_container.info("Starting response generation...")
                
                # Handle response.output_text.delta event (text streaming)
                elif chunk['type'] == 'response.output_text.delta':
                    # Append the new text delta to the full response
                    full_response += chunk['delta']['text']
                    placeholder.markdown(full_response)
                
                # Handle final response events
                elif chunk['type'] == 'final_response' or chunk['type'] == 'response.completed':
                    # Update with the final response after tool calls
                    if 'content' in chunk:
                        full_response = chunk['content']
                        placeholder.markdown(full_response)
                
                # Handle error events
                elif chunk['type'] == 'error':
                    st_container.error(f"Error: {chunk.get('message', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Error in process_streaming_response: {e}")
        st_container.error(f"An error occurred while processing the response: {str(e)}")
    
    return full_response

def handle_tool_call(tool_call, user_id=None):
    """
    Handle a tool call from the assistant.
    
    Args:
        tool_call: The tool call data
        user_id: The user's ID (None for guest users)
        
    Returns:
        Dict containing the tool call result
    """
    try:
        # Prepare the request payload
        payload = {
            "tool_call": tool_call
        }
        
        # Include user_id for authenticated users
        if user_id:
            payload["user_id"] = user_id
            path = '/customer_dashboard/api/ai_tool_call/'
        else:
            path = '/customer_dashboard/api/guest_ai_tool_call/'
            
        # Make the API call
        response = dj_post(
            path,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to process tool call.")
            return None
            
    except Exception as e:
        logging.error(f"Error in handle_tool_call: {e}")
        st.error("An error occurred while processing the tool call.")
        return None

def stream_chat_response(question, thread_id=None, user_id=None):
    """
    Stream a chat response from the assistant.
    
    Args:
        question: The user's message
        thread_id: Optional thread ID for continuing a conversation (now a response ID)
        user_id: The user's ID (None for guest users)
        
    Yields:
        Chunks of the assistant's response
    """
    try:
        # Prepare the request payload
        data = {
            "question": question
        }
        
        # Include user_id for authenticated users
        if user_id:
            data["user_id"] = user_id
            
        # Include thread_id if provided
        if thread_id:
            data["thread_id"] = thread_id
        else:
            data["thread_id"] = st.session_state.thread_id
        # Determine the URL based on whether it's a guest or authenticated user
        if user_id:
            path = '/customer_dashboard/api/assistant/stream-message/'
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        else:
            path = '/customer_dashboard/api/assistant/guest-stream-message/'
            headers = {}
        
        # Use our session-aware request helper to maintain cookies
        with dj_post(path, json=data, headers=headers, stream=True) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                yield data
                            except json.JSONDecodeError:
                                logging.error(f"Failed to decode JSON: {line[6:]}")
                        elif line.startswith('event: close'):
                            break
            else:
                st.error("Failed to stream response from assistant.")
                
    except Exception as e:
        logging.error(f"Error in stream_chat_response: {e}")
        st.error("An error occurred while streaming the response.")

def get_thread_detail(thread_id, user_id=None):
    """
    Get the details of a chat thread.
    
    Args:
        thread_id: The ID of the thread (now a response ID)
        user_id: The user's ID (None for guest users)
        
    Returns:
        The chat history
    """
    try:
        if user_id:
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            path = f'/customer_dashboard/api/thread_detail/{thread_id}/'
        else:
            headers = {}
            path = f'/customer_dashboard/api/guest_thread_detail/{thread_id}/'
            
        response = dj_get(
            path,
            headers=headers
        )
        
        if response.status_code == 200:
            chat_history = response.json().get('chat_history', [])
            
            # Sort chat_history by 'created_at' key
            chat_history.sort(key=lambda x: x['created_at'])
            
            return chat_history
        else:
            error_message = "Error fetching thread details."
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', error_message)
                except:
                    pass
            st.error(error_message)
            return []
    except Exception as e:
        logging.error(f"Error in get_thread_detail: {str(e)}")
        st.error("An error occurred while fetching thread details.")
        return []

def reset_conversation(user_id=None):
    """
    Reset a conversation with the assistant.
    
    Args:
        user_id: The user's ID (None for guest users)
        
    Returns:
        Dict containing the result of the reset operation
    """
    try:
        if user_id:
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            path = '/customer_dashboard/api/assistant/reset-conversation/'
            payload = {"user_id": user_id}
        else:
            # For guest users, reset Streamlit session variables
            # No need to generate guest_id as the persistent cookies will handle guest identification
            st.session_state.pop('response_id', None)
            st.session_state.pop('chat_history', None)
            st.session_state.pop('thread_id', None)
            
            # Call backend endpoint to reset any server-side state
            headers = {}
            path = '/customer_dashboard/api/assistant/guest-reset-conversation/'
            payload = {}
            
        response = dj_post(
            path,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to reset conversation.")
            return None
    except Exception as e:
        logging.error(f"Error in reset_conversation: {e}")
        st.error("An error occurred while resetting the conversation.")
        return None
    
def display_chat_message(role: str, content: str):
    """
    Display a chat message in the Streamlit UI.
    
    Args:
        role: The role of the message sender ('user' or 'assistant')
        content: The message content
    """
    with st.chat_message(role):
        st.markdown(content)

# ============================
# Onboarding Chat Helpers
# ============================

# TODO: Future enhancement - restore previous chat functionality
# def restore_pre_onboarding_chat():
#     """
#     Restore the chat history that was backed up before onboarding started.
#     Call this when user completes/cancels onboarding and wants to return to regular chat.
#     """
#     if 'pre_onboarding_chat_history' in st.session_state:
#         st.session_state['chat_history'] = st.session_state['pre_onboarding_chat_history'].copy()
#         st.session_state['thread_id'] = st.session_state.get('pre_onboarding_thread_id')
#         
#         # Clear the backup and onboarding flags
#         st.session_state.pop('pre_onboarding_chat_history', None)
#         st.session_state.pop('pre_onboarding_thread_id', None)
#         st.session_state.pop('onboarding_initialized', None)
#         
#         logging.info(f"Restored {len(st.session_state['chat_history'])} chat messages from pre-onboarding backup")
#         return True
#     return False

def clear_onboarding_state():
    """
    Clear all onboarding-related session state variables.
    Call this when onboarding is complete or cancelled.
    """
    onboarding_keys = [
        'onboarding_guest_id',
        'onboarding_chat_history', 
        'onboarding_response_id',
        'onboarding_complete',
        'show_password_modal',
        'onboarding_initialized'
    ]
    
    for key in onboarding_keys:
        st.session_state.pop(key, None)
    
    logging.info("Cleared all onboarding session state")

def start_onboarding_conversation(guest_id: Optional[str] = None) -> Optional[str]:
    """Start or reset the onboarding chat and return the guest_id."""
    payload = {}
    if guest_id:
        payload["guest_id"] = guest_id
    
    logging.info(f"Starting onboarding conversation with payload: {payload}")
    
    try:
        response = dj_post(
            "/customer_dashboard/api/assistant/onboarding/new-conversation/",
            json=payload,
        )
        logging.info(f"Onboarding API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            guest_id_returned = data.get("guest_id")
            logging.info(f"Onboarding API returned guest_id: {guest_id_returned}")
            return guest_id_returned
        else:
            logging.error(f"Onboarding API error: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error starting onboarding chat: {e}")
    return None


def onboarding_event_stream(message: str, guest_id: str, response_id: Optional[str] = None):
    """Yield SSE events from the onboarding assistant."""
    logging.info(f"Onboarding event stream called with guest_id: {guest_id}, message: {message[:50]}...")
    
    data = {"guest_id": guest_id, "message": message}
    if response_id:
        data["response_id"] = response_id
    
    logging.info(f"Sending onboarding stream request with data: {data}")

    with dj_post(
        "/customer_dashboard/api/assistant/onboarding/stream-message/",
        json=data,
        stream=True,
    ) as response:
        if response.status_code != 200:
            yield {"type": "error", "message": f"HTTP {response.status_code}"}
            return

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            decoded = raw_line.decode("utf-8")
            
            # Handle event: close
            if decoded.startswith("event:"):
                if "close" in decoded:
                    break
                continue
                
            if not decoded.startswith("data:"):
                continue
            payload = decoded[len("data:"):].strip()
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            yield event


def display_onboarding_stream(message: str, guest_id: str, response_id: Optional[str] = None):
    """Stream onboarding assistant text and capture tool output."""
    events = onboarding_event_stream(message, guest_id, response_id)
    accumulated = ""
    tool_output = None
    tool_name = None
    password_requested = False

    def text_gen():
        nonlocal accumulated, tool_output, tool_name, response_id, password_requested
        for ev in events:
            et = ev.get("type")
            
            if et == "response.created" and ev.get("id"):
                response_id = ev["id"]
            elif et == "response.output_text.delta":
                delta = ev.get("delta", {}).get("text", "") or ev.get("content", "")
                # de‑duplicate identical trailing chunks (same logic as main streaming function)
                if delta and not accumulated.endswith(delta):
                    accumulated += delta
                    yield delta
            elif et == "response.tool":
                tool_output = ev.get("output")
                tool_name = ev.get("name")
            elif et == "password_request":  # Handle password request events
                # Check the actual is_password_request value, not just the event type
                is_password_request = ev.get("is_password_request", False)
                if is_password_request:
                    password_requested = True
                    yield ""  # Yield empty to complete current stream
                    break
                # If is_password_request is False, just continue processing
                continue
            elif et == "response.completed":
                # Don't break here - continue processing to look for password_request event
                continue

    st.write_stream(text_gen())
    return response_id, accumulated, tool_name, tool_output, password_requested


def show_password_modal(guest_id: str) -> Optional[str]:
    """
    Display a secure password modal and handle submission.
    Returns the new access token if successful, None if cancelled/failed.
    """
    
    # Check if guest_id is None
    if guest_id is None:
        logging.error("show_password_modal called with guest_id=None")
        st.error("❌ Session error: Guest ID not found. Please restart the registration process.")
        if st.button("Restart Registration"):
            # Clear onboarding state and restart
            for key in ['onboarding_guest_id', 'onboarding_chat_history', 'onboarding_response_id', 'show_password_modal']:
                st.session_state.pop(key, None)
            st.rerun()
        return None
    
    @st.dialog("Complete Your Registration")
    def password_modal():
        st.write("🔐 **Secure Password Setup**")
        st.write("Your account information has been collected. Please create a secure password to complete your registration.")
        
        password = st.text_input(
            "Create Password", 
            type="password", 
            help="Must be at least 8 characters with a number, letter, and special character"
        )
        confirm_password = st.text_input("Confirm Password", type="password")
        
        # Real-time password validation
        if password:
            valid_password, password_msg = validate_input(password, 'password')
            if not valid_password:
                st.error(password_msg)
            elif confirm_password and password != confirm_password:
                st.error("Passwords do not match")
            elif password == confirm_password and valid_password:
                st.success("✅ Password meets requirements")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Complete Registration", type="primary", disabled=not (password and password == confirm_password and valid_password)):
                try:
                    # Submit to secure endpoint
                    payload = {
                        "guest_id": guest_id,
                        "password": password
                    }
                    logging.info(f"Submitting onboarding completion with guest_id: {guest_id}")
                    response = dj_post(
                        "/auth/api/secure-onboarding-complete/",
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Update session state with new user info
                        st.session_state['user_info'] = data
                        st.session_state['user_id'] = data.get('user_id')
                        st.session_state['access_token'] = data.get('access')
                        st.session_state['refresh_token'] = data.get('refresh')
                        st.session_state['is_logged_in'] = True
                        st.session_state['onboarding_complete'] = True
                        
                        st.success("🎉 Account created successfully!")
                        st.rerun()
                    else:
                        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                        error_msg = error_data.get('message', 'Registration failed. Please try again.')
                        st.error(f"❌ {error_msg}")
                        
                except Exception as e:
                    logging.error(f"Password submission error: {e}")
                    st.error("❌ Connection error. Please try again.")
        
        with col2:
            if st.button("Cancel"):
                st.session_state.pop('show_password_modal', None)
                st.rerun()
    
    # Show the modal
    password_modal()

# ============================
# Utility functions
# ============================
# Define a function to get the user's access token
def refresh_token(refresh_token):
    try:
        refresh_response = requests.post(
            f'{os.getenv("DJANGO_URL")}/auth/api/token/refresh/', 
            json={'refresh': refresh_token}
        )
        refresh_response.raise_for_status()
        return refresh_response.json() if refresh_response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        logging.error(f"Token refresh failed: {e}")
        st.error("Session expired. Please log in again.")
        return None

# Helper function to fetch follow-up recommendations
@st.fragment
def fetch_follow_up_recommendations(thread_id):
    """Fetch follow-up recommendations from the backend"""
    if not thread_id:
        st.session_state.recommend_follow_up = []
        return
        
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {'user_id': st.session_state.user_info['user_id']}
        # Include the thread_id in the request payload
        data['thread_id'] = thread_id
        
        
        follow_up_response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/recommend_follow_up/',
            method='post',
            headers=headers,
            data=data
        )
        
        if follow_up_response and follow_up_response.status_code == 200:

            # Unified parsing for follow-up recommendations
            response_json = follow_up_response.json()
            if isinstance(response_json, dict) and 'data' in response_json:
                data_list = response_json.get('data', [])
            elif isinstance(response_json, list):
                data_list = response_json
            else:
                data_list = []

            # Extract recommendation items from first entry
            recommend_items = []
            if data_list:
                first_entry = data_list[0]
                if isinstance(first_entry, str):
                    try:
                        payload = json.loads(first_entry)
                    except json.JSONDecodeError:
                        payload = {}
                elif isinstance(first_entry, dict):
                    payload = first_entry
                else:
                    payload = {}
                recommend_items = payload.get('items', [])

            # Set the recommendations to session state - as a dict with 'items' key
            # The UI expects a dictionary with 'items' key, not just the array
            st.session_state.recommend_follow_up = {'items': recommend_items} if recommend_items else []
        elif follow_up_response and follow_up_response.status_code == 404:
            # Backend API returned 404 - handle this gracefully
            st.session_state.recommend_follow_up = []
        else:
            st.session_state.recommend_follow_up = []
            logging.error(f"Failed to fetch follow-up recommendations, status: {follow_up_response.status_code if follow_up_response else 'N/A'}")
            
    except json.JSONDecodeError as e:
        st.session_state.recommend_follow_up = []
        logging.error(f"Error decoding follow-up JSON: {e}")
    except Exception as e:
        st.session_state.recommend_follow_up = []
        logging.error(f"Unexpected error processing follow-up recommendations: {e}")
        
def api_call_with_refresh(url, method='get', data=None, files=None, headers=None, params=None, stream=False):
    """
    Legacy wrapper function that will gradually be replaced with direct dj_* calls.
    This function still handles token refresh for authenticated users.
    """
    try:
        # Get the path from the full URL if using django_url
        path = url
        if django_url and url.startswith(django_url):
            path = url[len(django_url):]

        # Choose the right request format based on whether we're uploading files or sending JSON
        if files:
            session = get_api_session()
            if method.lower() == 'get':
                response = session.get(url, data=data, files=files, headers=headers, params=params, stream=stream)
            else:
                response = session.request(method, url, data=data, files=files, headers=headers, params=params, stream=stream)
        else:
            # Use our helper functions based on method
            if method.lower() == 'get':
                response = dj_get(path, params=params, headers=headers, stream=stream)
            elif method.lower() == 'post':
                response = dj_post(path, json=data, headers=headers, params=params, stream=stream)
            elif method.lower() == 'put':
                response = dj_put(path, json=data, headers=headers, params=params, stream=stream)
            elif method.lower() == 'delete':
                response = dj_delete(path, json=data, headers=headers, params=params, stream=stream)
            else:
                response = get_api_session().request(method, url, json=data, headers=headers, params=params, stream=stream)
            
        if response.status_code == 401 and 'user_info' in st.session_state:  # Token expired
            new_tokens = refresh_token(st.session_state.user_info["refresh"])
            if new_tokens:
                st.session_state.user_info.update(new_tokens)
                if headers is None:
                    headers = {}
                headers['Authorization'] = f'Bearer {new_tokens["access"]}'
                
                # Retry with new token, again handling files appropriately
                if files:
                    session = get_api_session()
                    if method.lower() == 'get':
                        response = session.get(url, data=data, files=files, headers=headers, params=params, stream=stream)
                    else:
                        response = session.request(method, url, data=data, files=files, headers=headers, params=params, stream=stream)
                else:
                    # Use our helper functions based on method
                    if method.lower() == 'get':
                        response = dj_get(path, params=params, headers=headers, stream=stream)
                    elif method.lower() == 'post':
                        response = dj_post(path, json=data, headers=headers, params=params, stream=stream)
                    elif method.lower() == 'put':
                        response = dj_put(path, json=data, headers=headers, params=params, stream=stream)
                    elif method.lower() == 'delete':
                        response = dj_delete(path, json=data, headers=headers, params=params, stream=stream)
                    else:
                        response = get_api_session().request(method, url, json=data, headers=headers, params=params, stream=stream)
        
        # For error status codes, handle appropriately
        if response.status_code >= 400 and not stream:  # Don't try to parse JSON for streaming responses
            logging.error(f"API error: {response.status_code} for {url}")
            try:
                response_data = response.json()
                if isinstance(response_data, dict):
                    if 'status' in response_data and 'message' in response_data:
                        if response_data['status'] == 'error':
                            st.error(response_data['message'])
                    else:
                        error_message = response_data.get('message', 
                                      response_data.get('error', 
                                      response_data.get('detail', f"Error {response.status_code}")))
                        st.error(error_message)
            except Exception as e:
                logging.error(f"Error parsing response: {str(e)}")
                st.error(f"Error {response.status_code}: {response.text[:100]}")
            
        return response
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error: {req_err}")
        st.error("A network error occurred. Please check your connection and try again.")
        return None

# Define a function to check if a user is authenticated
def is_user_authenticated():
    result = 'user_info' in st.session_state and 'access' in st.session_state.user_info
    return result


# Function to check summary status
def check_summary_status(user_id, headers, max_attempts=10):
    attempts = 0
    try:
        while attempts < max_attempts:
            response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_summary_status/',
                method='get',
                headers=headers,
                data={"user_id": user_id}
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'error')
                if status == 'completed':
                    return 'completed'
                elif status == 'error':
                    return 'error'
            attempts += 1
            time.sleep(5)  # Wait before retrying
        return 'timeout'
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error in check_summary_status: {e}")
        st.error("A network error occurred. Please check your connection and try again.")
        return 'error'
    except Exception as e:
        logging.error(f"Exception in check_summary_status: {e}")
        st.error("An unexpected error occurred. Please try again later.")
        return 'error'

def get_user_summary(user_id, headers):
    try:
        # Prepare the data payload
        data = {"user_id": user_id}
            
        # Make a direct call to the user_summary endpoint
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_summary/',
            method='get',
            headers=headers,
            data=data
        )
        
        if not response:
            st.error("Failed to connect to the server.")
            return None
            
        # Handle different status codes
        if response.status_code == 200:
            # Summary is complete and available
            return response.json()
        elif response.status_code == 202:
            # Summary is still being generated
            data = response.json()
            st.info(data.get('message', 'Summary is being generated. Please wait.'))
            return {"status": "pending"}
        else:
            st.error(f"Error fetching summary: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error in get_user_summary: {e}")
        st.error("A network error occurred. Please check your connection and try again.")
        return None
    except Exception as e:
        logging.error(f"Exception in get_user_summary: {e}")
        st.error("An unexpected error occurred. Please try again later.")
        return None

def stream_user_summary(date=None):
    """
    Stream a user daily summary from the backend.
    
    Args:
        date: Optional date for the summary (default: today)
        
    Yields:
        Summary data chunks and progress updates
    """
    try:
        # Ensure user is authenticated
        if not is_user_authenticated():
            st.error("You must be logged in to view summaries")
            return
            
        # Prepare the request params
        params = {}
        if date:
            params['date'] = date
            
        # Make the streaming request
        url = f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/stream_user_summary/'
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        sent_any_deltas = False  # Flag to track if we've yielded any delta events
        buf = ""  # Buffer to accumulate text for potential final yield
        
        with requests.get(url, params=params, headers=headers, stream=True) as response:
            if response.status_code != 200:
                st.error(f"Error: {response.status_code}")
                return

            # Process the streaming response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            
                            # Check if this is a text delta event
                            if isinstance(data, dict) and data.get("type") == "text":
                                sent_any_deltas = True
                                buf += data.get("content", "")
                                yield data
                            elif isinstance(data, dict) and data.get("type") == "ResponseTextDeltaEvent":
                                sent_any_deltas = True
                                buf += data.get("delta", "")
                                yield {"type": "text", "content": data.get("delta", "")}
                            else:
                                # For all other event types, just pass them through
                                yield data
                                
                        except json.JSONDecodeError:
                            logging.error(f"Failed to decode JSON: {line[6:]}")
            
            # After the loop, check if we need to yield the buffer as a complete text
            if buf and not sent_any_deltas:  # Only yield if no deltas were sent
                yield {"type": "text", "content": buf}
                            
    except Exception as e:
        logging.error(f"Error in stream_user_summary: {e}")
        yield {"type": "error", "message": f"An error occurred: {str(e)}"}

def display_streaming_summary(date=None):
    """Display a streaming summary in Streamlit"""
    
    # summary_container = st.empty()
    progress_container = st.empty()
    
    try:
        summary_text = ""
        summary_data = None
        
        for event in stream_user_summary(date):
            event_type = event.get("type")
            
            # Handle different event types
            if event_type == "status":
                status = event.get("status")
                if status == "starting":
                    progress_container.info("Preparing your summary...")
                elif status == "pending":
                    # Show progress if available
                    progress = event.get("progress", "")
                    if progress:
                        progress_container.info(f"Generating summary... {progress}")
                    else:
                        progress_container.info("Generating summary...")
            
            # Handle text content (deltas or complete)
            elif event_type == "text":
                content = event.get("content", "")
                if content:
                    summary_text += content
                    # summary_container.markdown(summary_text)
            
            # Handle summary content
            elif event_type == "summary":
                summary_data = event
                summary_text = event.get("summary", "")
                # summary_container.markdown(summary_text)
                progress_container.empty()  # Clear the progress message
            
            # Handle errors
            elif event_type == "error":
                error_msg = event.get("message", "An unknown error occurred")
                progress_container.error(error_msg)
            
            # End of stream marker
            elif event_type == "end":
                break
        
        # If we accumulated text but didn't get a formal summary event
        if summary_text and not summary_data:
            summary_data = {"summary": summary_text}
        
        # Clear any progress messages
        progress_container.empty()
                
        # Return the complete summary data
        return summary_data
        
    except Exception as e:
        logging.error(f"Error displaying summary: {e}")
        progress_container.error(f"Error: {str(e)}")
        return None

def show_daily_summary_page():
    st.title("Your Daily Summary")
    
    # Add date selector
    date = st.date_input("Select date", value=None)
    date_str = date.strftime('%Y-%m-%d') if date else None
    
    if st.button("Get Summary"):
        with st.spinner("Fetching your summary..."):
            summary_data = display_streaming_summary(date_str)
            
            if summary_data:
                # Show additional information
                st.success("Summary completed!")
                
                # Optionally, save the summary to session state
                st.session_state.last_summary = summary_data
                            
def switch_user_role():
    try:
        # This function will call your Django backend to switch the user's role
        api_url = f"{os.getenv('DJANGO_URL')}/auth/api/switch_role/"
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(api_url, method='post', headers=headers)
        if response:
            return response.json() if response.status_code == 200 else None
    except Exception as e:
        logging.error(f"Failed to switch user role: {e}")
        st.error("Unable to switch roles at the moment. Please try again later.")
        return None

def login_form():
    with st.expander("Login", expanded=False):
        st.write("Login to your account.")
        with st.form(key='login_form'):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button(label='Login')
            register_button = st.form_submit_button(label="Register")

        if submit_button:
            if validate_input(username, 'username') and validate_input(password, 'password'):
                try:
                    # Preserve navigation state
                    navigation_state = st.session_state.get("navigation", None)
                    
                    # Remove guest user from session state
                    for key in list(st.session_state.keys()):
                        if key != "navigation":  # Don't delete navigation state
                            del st.session_state[key]
                            
                    # Restore navigation state if it existed
                    if navigation_state:
                        st.session_state["navigation"] = navigation_state
                        
                    # API call to get the token
                    response = requests.post(
                        f'{os.getenv("DJANGO_URL")}/auth/api/login/',
                        json={'username': username, 'password': password}
                    )
                    if response.status_code == 200:
                        response_data = response.json()
                        logging.info(f"Login successful: is_chef={response_data.get('is_chef')}, current_role={response_data.get('current_role')}")
                        st.success("Logged in successfully!")
                        # Update session state with user information
                        st.session_state['user_info'] = response_data
                        st.session_state['user_id'] = response_data['user_id']
                        st.session_state['email_confirmed'] = response_data['email_confirmed']
                        st.session_state['is_chef'] = response_data['is_chef']  # Include the is_chef attribute in the session state
                        st.session_state['timezone'] = response_data['timezone']
                        st.session_state['preferred_language'] = response_data['preferred_language']
                        st.session_state['dietary_preferences'] = response_data['dietary_preferences']
                        st.session_state['custom_dietary_preferences'] = response_data.get('custom_dietary_preferences', []) 
                        st.session_state['emergency_supply_goal'] = response_data.get('emergency_supply_goal', 0)
                        st.session_state['household_member_count'] = response_data.get('household_member_count', 1)
                        
                        # Enhanced handling for household members during login
                        household_members = response_data.get('household_members', [])
                        if household_members is None:
                            household_members = []
                        st.session_state['household_members'] = household_members
                        logging.info(f"Login: Set household members in session state: {len(household_members)} member(s) - {household_members}")
                        st.session_state['allergies'] = response_data['allergies']
                        st.session_state['custom_allergies'] = response_data['custom_allergies']
                        st.session_state['goal_name'] = response_data['goal_name']
                        st.session_state['goal_description'] = response_data['goal_description']
                        st.session_state['current_role'] = response_data['current_role']
                        st.session_state['access_token'] = response_data['access']
                        st.session_state['refresh_token'] = response_data['refresh']
                        st.session_state['is_logged_in'] = True
                        logging.info(f"Session state set: is_chef={st.session_state.get('is_chef')}, current_role={st.session_state.get('current_role')}")
                        st.rerun()  # Rerun to update navigation
                except requests.exceptions.HTTPError as http_err:
                    st.error("Invalid username or password.")
                    logging.warning(f"Login failed: {http_err}")
                except requests.exceptions.RequestException as req_err:
                    st.error("A network error occurred. Please check your connection and try again.")
                    logging.error(f"Network error during login: {req_err}")
                except Exception as e:
                    st.error("An unexpected error occurred during login.")
                    logging.error(f"Unexpected error during login: {e}")

        if register_button:
            # Set a session state variable to indicate navigation to register page
            navigate_to_page('register')

        # Password Reset Button
        if st.button("Forgot your password?"):
            # Set a session state variable to indicate navigation to account page
            navigate_to_page('account')


def resend_activation_link(user_id):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            method='post', 
            url = f'{os.getenv("DJANGO_URL")}/auth/api/resend-activation-link/',
            data ={'user_id': user_id},
            headers=headers
        )
        response.raise_for_status()
        if response.status_code == 200:
            st.success("A new activation link has been sent to your email.")
    except requests.exceptions.RequestException as e:
        st.error("Failed to resend activation link. Please try again later.")
        logging.error(f"Error resending activation link: {e}")

def fetch_and_update_user_profile():
    try:
        if is_user_authenticated():
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

            # Fetch user details
            user_response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', headers=headers)
            if user_response.status_code == 200:
                user_data = user_response.json()
                st.session_state['user_id'] = user_data['id']
                st.session_state['email_confirmed'] = user_data['email_confirmed']
                st.session_state['is_chef'] = user_data.get('is_chef', False)
                st.session_state['timezone'] = user_data['timezone']
                st.session_state['preferred_language'] = user_data['preferred_language']
                st.session_state['dietary_preferences'] = user_data['dietary_preferences']
                st.session_state['custom_dietary_preferences'] = user_data.get('custom_dietary_preferences', [])  # Updated key and default
                st.session_state['allergies'] = user_data['allergies']
                st.session_state['custom_allergies'] = user_data['custom_allergies']
                st.session_state['household_member_count'] = user_data.get('household_member_count', 1)
                
                # Enhanced handling for household members
                household_members = user_data.get('household_members', [])
                if household_members is None:
                    household_members = []
                st.session_state['household_members'] = household_members
                logging.info(f"Fetched household members from backend: {len(household_members)} member(s) - {household_members}")
                
                st.session_state['goal_name'] = user_data['goals']['goal_name'] if user_data.get('goals') else ""
                st.session_state['goal_description'] = user_data['goals']['goal_description'] if user_data.get('goals') else ""
                st.session_state['current_role'] = user_data.get('current_role', '')
            else:
                st.error("Failed to fetch user profile.")
                logging.error(f"Failed to fetch user profile: {user_response.status_code} - {user_response.text if user_response else 'No response'}")

            # Fetch address details
            address_response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/address_details/', headers=headers)
            if address_response.status_code == 200:
                address_data = address_response.json()
                st.session_state['address'] = {
                    'street': address_data.get('street', ''),
                    'city': address_data.get('city', ''),
                    'state': address_data.get('state', ''),
                    'postalcode': address_data.get('input_postalcode', ''),
                    'country': address_data.get('country', '')
                }
            else:
                st.error("Failed to fetch address details.")
    except requests.exceptions.RequestException as req_err:
        st.error("A network error occurred. Please check your connection and try again.")
        logging.error(f"Network error during profile fetch: {req_err}")
    except Exception as e:
        st.error("An unexpected error occurred while fetching the user profile.")
        logging.error(f"Unexpected error during profile fetch: {e}")    

def toggle_chef_mode():
    try:    
        # Ensure 'user_info' exists, contains 'is_chef', and user is authorized as a chef
        if 'user_info' in st.session_state and st.session_state['user_info'].get('is_chef', False):
            
            # Display the toggle only if the user is authorized to be a chef
            chef_mode = st.toggle("Switch Chef | Customer", value=st.session_state['user_info'].get('current_role') == 'chef', key="chef_mode_toggle")
                
            # Check if there's a change in the toggle state compared to 'user_info'
            if ((chef_mode and st.session_state['user_info']['current_role'] != 'chef') or
                (not chef_mode and st.session_state['user_info']['current_role'] != 'customer')):
            
                # Call the backend to switch the user role
                result = switch_user_role()
                
                if result:  # If role switch is successful, update 'user_info' in session state
                    # Preserve navigation state
                    navigation_state = st.session_state.get("navigation", None)
                    
                    # Assuming 'result' properly reflects the updated role
                    new_role = 'chef' if chef_mode else 'customer'
                    st.session_state['current_role'] = new_role
                    st.session_state['user_info']['current_role'] = new_role
                    
                    # Restore navigation state
                    if navigation_state:
                        st.session_state["navigation"] = navigation_state
                        
                    st.rerun()
                else:
                    # If role switch failed, inform the user and revert the toggle to reflect actual user role
                    st.error("Failed to switch roles.")
                    # No need to rerun here; just display the error message and keep the state consistent
    except Exception as e:
        st.error("An unexpected error occurred while trying to switch roles.")
        logging.error(f"Exception in toggle_chef_mode: {e}")    


# ============================
# Legacy EventHandler (kept for compatibility)
# ============================
class EventHandler(AssistantEventHandler):
    def __init__(self, thread_id, chat_container=None, user_id=None):
        super().__init__()
        self.output = None
        self.tool_id = None
        self.function_arguments = None
        self.thread_id = thread_id
        self.run_id = None
        self.run_step = None
        self.function_name = ""
        self.arguments = ""
        self.tool_calls = []
        self.user_id = user_id
        self.chat_container = chat_container
        self.headers = {
            "OpenAI-Beta": "assistants=v2",
            "Content-Type": "application/json"
        }

    def response_generator(self, response_text):
        words = response_text.split(' ')
        for word in words:
            if word == '\n':
                yield word
            else:
                yield word + ' '
            time.sleep(0.05)


    @override
    def on_text_created(self, text) -> None:
        pass



    @override
    def on_text_delta(self, delta, snapshot):
        pass

    def on_text_done(self, text) -> None:
        if self.chat_container:
            response_text = text.value
            with self.chat_container.chat_message("assistant"):
                st.write_stream(self.response_generator(response_text))
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    def on_end(self):
        tool_outputs = []
        if self.current_run_step_snapshot and self.current_run_step_snapshot.step_details.type == 'tool_calls':
            for tool_call in self.current_run_step_snapshot.step_details.tool_calls:
                tool_call_data = {
                    "id": tool_call.id,
                    "function": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
                if is_user_authenticated():
                    tool_call_result = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/ai_tool_call/',
                        method='post',
                        data={"user_id": self.user_id, "tool_call": tool_call_data} 
                    )
                else:
                    tool_call_result = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/guest_ai_tool_call/',
                        method='post',
                        data={"tool_call": tool_call_data}
                    )                    
                if tool_call_result.status_code == 200:
                    # Serialize the output to JSON string if it's a dictionary/object
                    result_data = tool_call_result.json()
                    output_str = json.dumps(result_data['output'])
                    tool_outputs.append({
                        "tool_call_id": result_data['tool_call_id'],
                        "output": output_str  # Ensure output is a JSON string
                    })
        if tool_outputs:
            with client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=self.thread_id,
                run_id=self.run_id,
                tool_outputs=tool_outputs,
                event_handler=EventHandler(self.thread_id, chat_container=self.chat_container, user_id=self.user_id),
                extra_headers=self.headers
            ) as stream:
                stream.until_done()


    @override
    def on_exception(self, exception: Exception) -> None:
        logging.error(f"Exception: {exception}")
        st.error("An unexpected error occurred. Please try again later.")

    @override
    def on_message_created(self, message: Message) -> None:
        pass

    @override
    def on_message_done(self, message: Message) -> None:
        pass

    @override
    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        pass


    @override
    def on_tool_call_done(self, tool_call: ToolCall) -> None:       
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=self.thread_id,
            run_id=self.run_id,
            extra_headers=self.headers
        )


        if keep_retrieving_run.status == "completed":
            all_messages = client.beta.threads.messages.list(
                thread_id=self.thread_id,
                extra_headers=self.headers
            )
            return

        elif keep_retrieving_run.status == "requires_action":
            pass
        else:
            pass

    @override
    def on_run_step_created(self, run_step: RunStep) -> None:
        self.run_id = run_step.run_id
        self.run_step = run_step

    @override
    def on_run_step_done(self, run_step: RunStep) -> None:
        pass

    def on_tool_call_delta(self, delta, snapshot): 
        if delta.type == 'function':
            self.arguments += delta.function.arguments
        elif delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                pass
            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        pass
        else:
            pass
        
    @override
    def on_event(self, event: AssistantStreamEvent) -> None:
        if event.event == "thread.run.requires_action":
            pass

def check_django_cookies():
    """
    Check if Django session cookies are present in the current session.
    Warns the user if cookies are blocked, as this will break session continuity.
    """
    session = get_api_session()
    
    # Make a simple request to any non-authenticated Django endpoint
    response = session.get(f"{django_url}/health/")
    
    # Check for Django's sessionid cookie after the request
    if not session.cookies.get("sessionid"):
        st.warning(
            "We couldn't store a session cookie. This may limit functionality for guest users. "
            "If you're running an ad-blocker or anti-tracking extension, please allow cookies for this site."
        )
        return False
    return True

def new_idem_key() -> str:
    """Return a fresh v4 uuid for Idempotency-Key headers."""
    return str(uuid.uuid4())

def place_chef_order(meal_event_id: int, qty: int, special=""):
    hdr = {
        "Authorization": f"Bearer {st.session_state.user_info['access']}",
        "Idempotency-Key": new_idem_key()
    }
    data = {"meal_event": meal_event_id, "quantity": qty, "special_requests": special}
    return api_call_with_refresh(
        url=f"{django_url}/meals/api/chef-meal-orders/",
        method="post",
        data=data,
        headers=hdr,
    )

def adjust_chef_order(order_id: int, qty: int):
    hdr = {
        "Authorization": f"Bearer {st.session_state.user_info['access']}",
        "Idempotency-Key": new_idem_key()
    }
    return api_call_with_refresh(
        url=f"{django_url}/meals/api/chef-meal-orders/{order_id}/adjust-quantity/",
        method="patch",
        data={"quantity": qty},
        headers=hdr,
    )

# ============================
# Navigation Utility Functions
# ============================
def navigate_to_page(page_key):
    """
    Navigate to a specific page using the modern Streamlit navigation system.
    
    Args:
        page_key (str): The key identifying the target page
                       Options: 'home', 'assistant', 'meal_plans', 'pantry', 'history', 
                               'account', 'profile', 'register', 'chef_meals', 'chef_application'
    """
    st.session_state['navigate_to'] = page_key
    st.rerun()
