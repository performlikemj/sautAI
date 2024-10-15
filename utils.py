import json
from random import sample
from collections import defaultdict
import os
import time
from typing_extensions import override
import openai
from openai import OpenAIError
from openai import AssistantEventHandler, OpenAI
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

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

# Retrieve the environment variable in Python
django_url = os.getenv("DJANGO_URL")

openai_env_key = os.getenv("OPENAI_KEY")

if openai_env_key:
    openai.api_key = openai_env_key

client = openai

openai_headers = {
    "Content-Type": "application/json",
    "OpenAI-Beta": "assistants=v2",
}

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


# Use this in your API calls
def api_call_with_refresh(url, method='get', data=None, headers=None):
    try:
        response = requests.request(method, url, json=data, headers=headers)
        if response.status_code == 401:  # Token expired
            new_tokens = refresh_token(st.session_state.user_info["refresh"])
            if new_tokens:
                st.session_state.user_info.update(new_tokens)

                headers['Authorization'] = f'Bearer {new_tokens["access"]}'
                response = requests.request(method, url, json=data, headers=headers)  # Retry with new token
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        st.error("An error occurred while connecting to the server. Please try again.")
        return None
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error: {req_err}")
        st.error("A network error occurred. Please check your connection and try again.")
        return None

# Define a function to check if a user is authenticated
def is_user_authenticated():
    return 'user_info' in st.session_state and 'access' in st.session_state.user_info


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
        status = check_summary_status(user_id, headers)
        if status == 'completed':
            response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_summary/',
                method='get',
                headers=headers,
                data={"user_id": user_id}
            )
            if response.status_code == 200:
                return response.json()  # Return the summary data
        elif status == 'error':
            st.error("An error occurred while generating the summary.")
        elif status == 'timeout':
            st.warning("Summary generation is taking longer than expected. Please try again later.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error in get_user_summary: {e}")
        st.error("A network error occurred. Please check your connection and try again.")
        return None
    except Exception as e:
        logging.error(f"Exception in get_user_summary: {e}")
        st.error("An unexpected error occurred. Please try again later.")
        return None

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
                    # Remove guest user from session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    # API call to get the token
                    response = requests.post(
                        f'{os.getenv("DJANGO_URL")}/auth/api/login/',
                        json={'username': username, 'password': password}
                    )
                    if response.status_code == 200:
                        response_data = response.json()
                        st.success("Logged in successfully!")
                        # Update session state with user information
                        st.session_state['user_info'] = response_data
                        st.session_state['user_id'] = response_data['user_id']
                        st.session_state['email_confirmed'] = response_data['email_confirmed']
                        st.session_state['is_chef'] = response_data['is_chef']  # Include the is_chef attribute in the session state
                        st.session_state['timezone'] = response_data['timezone']
                        st.session_state['preferred_language'] = response_data['preferred_language']
                        st.session_state['dietary_preferences'] = response_data['dietary_preferences']
                        st.session_state['custom_dietary_preferences'] = response_data.get('custom_dietary_preferences', [])  # Updated key and default
                        st.session_state['allergies'] = response_data['allergies']
                        st.session_state['custom_allergies'] = response_data['custom_allergies']
                        st.session_state['goal_name'] = response_data['goal_name']
                        st.session_state['goal_description'] = response_data['goal_description']
                        st.session_state['current_role'] = response_data['current_role']
                        st.session_state['access_token'] = response_data['access']
                        st.session_state['refresh_token'] = response_data['refresh']
                        st.session_state['is_logged_in'] = True
                        st.rerun()  # Rerun the script to reflect the login state
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
            st.switch_page("pages/7_register.py")

        # Password Reset Button
        if st.button("Forgot your password?"):
            # Directly navigate to the activate page for password reset
            st.switch_page("pages/5_account.py")

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
                st.session_state['goal_name'] = user_data['goals']['goal_name'] if user_data.get('goals') else ""
                st.session_state['goal_description'] = user_data['goals']['goal_description'] if user_data.get('goals') else ""
                st.session_state['current_role'] = user_data.get('current_role', '')
            else:
                st.error("Failed to fetch user profile.")

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
                    # Assuming 'result' properly reflects the updated role
                    new_role = 'chef' if chef_mode else 'customer'
                    st.session_state['current_role'] = new_role
                    st.session_state['user_info']['current_role'] = new_role
                    st.rerun()
                else:
                    # If role switch failed, inform the user and revert the toggle to reflect actual user role
                    st.error("Failed to switch roles.")
                    # No need to rerun here; just display the error message and keep the state consistent
    except Exception as e:
        st.error("An unexpected error occurred while trying to switch roles.")
        logging.error(f"Exception in toggle_chef_mode: {e}")    

def guest_chat_with_gpt(prompt, thread_id):
    try:
        url = f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/guest_chat_with_gpt/'
        payload = {'question': prompt, 'thread_id': thread_id}
        headers = {'Content-Type': 'application/json'}

        response_data = requests.post(url, json=payload, headers=headers)

        if response_data.status_code == 200:
            return response_data.json()
        if response_data.status_code == 429:  # Rate limit status code
            st.error("You've exceeded the rate limit. Please try again later or consider registering.")
        else:
            st.error("Failed to get response from the chatbot.")
            return None
    except requests.exceptions.RequestException as e:
        st.error("A network error occurred. Please check your connection and try again.")
        logging.error(f"Request error in guest_chat_with_gpt: {e}")
        return None
    except Exception as e:
        st.error("An unexpected error occurred while communicating with the chatbot.")
        logging.error(f"Exception in guest_chat_with_gpt: {e}")
        return None    

def chat_with_gpt(prompt, thread_id, user_id):
    try:
        response_data = requests.post(
            f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/chat_with_gpt/', 
            data={'question': prompt, 'thread_id': thread_id, 'user_id': user_id}
        )
        if response_data.status_code == 200:
            return response_data.json()
        else:
            st.error("Sorry. There was an error communicating with your assistant. Please try again.")
            return None
    except requests.exceptions.RequestException as e:
        st.error("A network error occurred. Please check your connection and try again.")
        logging.error(f"Request error in chat_with_gpt: {e}")
        return None
    except Exception as e:
        st.error("An unexpected error occurred while communicating with the chatbot.")
        logging.error(f"Exception in chat_with_gpt: {e}")
        return None    
    
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
        # if self.chat_container:
            # response_text = text.value  # Ensure this line correctly extracts the text value.
            # print(f"Streaming response text: {response_text}")  # Debug print
            # with self.chat_container.chat_message("assistant"):
            #     st.write_stream(self.response_generator(response_text))
            # st.session_state.chat_history.append({"role": "assistant", "content": response_text})


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


def start_or_continue_streaming(client, user_id, openai_headers, chat_container = None, user_details_prompt=None, prompt=None, change_meals=False):
    try:
        # Ensure thread_id is set to None if not present in session state
        st.session_state.thread_id = st.session_state.get('thread_id', None)
        # Start or continue streaming responses
        with client.beta.threads.runs.stream(
            thread_id=st.session_state.thread_id,
            assistant_id=os.getenv("ASSISTANT_ID") if is_user_authenticated() else os.getenv("GUEST_ASSISTANT_ID"),
            event_handler=EventHandler(st.session_state.thread_id, chat_container, user_id),
            instructions=user_details_prompt if is_user_authenticated() else prompt,  # Or set general instructions for your assistant
            extra_headers=openai_headers,
            tool_choice= "auto" if not change_meals else {"type": "function", "function": {"name": "replace_meal_based_on_preferences"}}
        ) as stream:
            stream.until_done()
    except openai.BadRequestError as e:
        if 'already has an active run' in str(e):
            st.session_state.thread_id = None
            logging.error(e)
            st.error("The current thread already has an active run. Please start a new chat.")
    except OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        st.error("An error occurred with the AI assistant. Please try again later.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        st.error("An unexpected error occurred. Please try again later.")

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