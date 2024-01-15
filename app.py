import streamlit as st
import streamlit_ace as st_ace
from dotenv import load_dotenv
import openai
import os
import json
import re
import time
from openai import OpenAIError
from utils import auth_search_dishes
import requests
load_dotenv()
from elasticsearch import Elasticsearch

es = Elasticsearch(
  os.getenv("ELASTIC_URL"),
  api_key= os.getenv("ELASTIC_API_KEY")
)


openai_env_key = os.getenv("OPENAI_KEY")

if openai_env_key:
    openai.api_key = openai_env_key

client = openai

functions = {
    "auth_search_dishes": auth_search_dishes,
}


def ai_call(tool_call, user_info):
    function = tool_call.function
    name = function.name
    arguments = json.loads(function.arguments)

    # Add the user input to the arguments
    arguments['user_input'] = user_info

    # Call the function and get the return value
    # Note: 'functions' should be a dictionary mapping function names to function objects
    return_value = functions[name](**arguments)

    # Prepare the tool outputs
    tool_outputs = {
        "tool_call_id": tool_call.id,
        "output": return_value,
    }

    return tool_outputs

def handle_openai_communication(question, thread_id, user_info = None):
    assistant_id = os.getenv("ASSISTANT_ID")
    # Check if question is provided
    if not question:
        return {'error': 'No question provided'}

    # Check if thread_id is safe
    if thread_id and not re.match("^thread_[a-zA-Z0-9]*$", thread_id):
        return {'error': 'Invalid thread_id'}

    # Handle existing or new thread
    if not thread_id:
        try:
            openai_thread = client.beta.threads.create()
            thread_id = openai_thread.id
        except OpenAIError as e:
            return {'error': f'Failed to create thread: {str(e)}'}

    try:
        # Add a Message to a Thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=question
        )
    except OpenAIError as e:
        return {'error': f'Failed to create message: {str(e)}'}

    # Variable to store tool call results
    formatted_outputs = []

    try:
        # Run the Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            # Optionally, you can add specific instructions here
        )
    except OpenAIError as e:
        return {'error': f'Failed to create run: {str(e)}'}

    # Check the status of the Run and retrieve responses
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == 'completed':
            print('Run completed')
            break
        elif run.status == 'failed':
            print('Run failed')
            break
        elif run.status in ['expired', 'cancelled']:
            print(f'Run {run.status}')
            break
        elif run.status in ['failed', 'queued', 'in_progress']:
            time.sleep(0.5)
            continue
        elif run.status == "requires_action":
            tool_outputs = []
            print("Run requires action")
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                # Execute the function call and get the result
                tool_call_result = ai_call(tool_call, user_info)
                
                # Extracting the tool_call_id and the output
                tool_call_id = tool_call_result['tool_call_id']
                output = tool_call_result['output']
                
                # Assuming 'output' needs to be serialized as a JSON string
                # If it's already a string or another format is required, adjust this line accordingly
                output_json = json.dumps(output)

                # Prepare the output in the required format
                formatted_output = {
                    "tool_call_id": tool_call_id,
                    "output": output_json
                }
                tool_outputs.append(formatted_output)

                formatted_outputs.append(formatted_output)
                
            # Submitting the formatted outputs
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs,
            )
            continue

    return formatted_outputs

def main():
    # Set the title of the app
    st.title("SautAI")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a Page:", ["Home", "Activate", "Register", "Assistant", "Profile"])

    # Home Page
    if page == "Home":
        st.header("Welcome to sautAI!")
        st.write("This is the home page of our app.")

    # Activate Page
    elif page == "Activate":
        st.header("Account Activation")
        query_params = st.experimental_get_query_params()
        uid = query_params.get("uid", [""])[0]  # Extract first item from list
        token = query_params.get("token", [""])[0]  # Extract first item from list

        if st.button("Activate Account"):
            # Send activation request to Django API
            response = requests.post(f'{os.getenv("DJANGO_URL")}/activate_account/', data={'uid': uid, 'token': token})
            if response.status_code == 200:
                st.success("Account activated successfully!")
            else:
                st.error("Account activation failed.")

    # Profile Page
    elif page == "Profile":
        st.header("Your Profile")
        st.write("This is your profile page. Help your assistant make better decisions by filling out the following information:")

        # Create a form
        with st.form(key='profile_form'):
            dietary_preference = st.text_input("Dietary Preference:")
            allergies = st.text_input("Allergies:")
            dietary_goals = st.text_input("Dietary Goals:")

            # Address fields
            st.subheader("Address")
            street = st.text_input("Street:")
            city = st.text_input("City:")
            state_province = st.text_input("State/Province:")
            country = st.text_input("Country:")
            postal_code = st.text_input("Postal Code:")

            # When the user presses the 'Submit' button, store the input values in the session state
            submit_button = st.form_submit_button(label='Submit')
            if submit_button:
                user_info = {
                    "dietary_preference": dietary_preference,
                    "allergies": allergies,
                    "dietary_goals": dietary_goals,
                    "address": {
                        "street": street,
                        "city": city,
                        "state_province": state_province,
                        "country": country,
                        "postal_code": postal_code
                    }
                }
                es.index(index="user", id=user_id,body=user_info)
                st.session_state.user_info = user_info

    # Registration Page
    elif page == "Register":
        st.header("Register")
        st.write("Create an account.")

        with st.form(key='registration_form'):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            phone_number = st.text_input("Phone Number")
            dietary_preferences = [ 'Vegan', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Everything']
            dietary_preference = st.selectbox("Dietary Preference", dietary_preferences)

            # Address fields
            st.subheader("Address")
            street = st.text_input("Street")
            city = st.text_input("City")
            state = st.text_input("State/Province")
            country = st.text_input("Country")
            postal_code = st.text_input("Postal Code")

            submit_button = st.form_submit_button(label='Register')
            if submit_button:
                if len(country) != 2 or not country.isalpha():
                    st.error("Please enter a valid two-letter country code.")
                else:
                    # Construct the data payload for the API request
                    user_data = {
                        "user": {
                            "username": username,
                            "email": email,
                            "password": password,
                            "phone_number": phone_number,
                            "dietary_preference": dietary_preference
                        },
                        "address": {
                            "street": street,
                            "city": city,
                            "state": state,
                            "country": country,
                            "postalcode": postal_code
                        }
                    }

                    # API endpoint URL
                    api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"

                    # Send the POST request to your Django API
                    response = requests.post(api_url, json=user_data)

                    if response.status_code == 200:
                        st.success("Registration successful!")
                        response_data = response.json()
                        if 'navigate_to' in response_data:
                            # Update the page based on the response
                            page = response_data['navigate_to']
                            st.rerun()
                        # Handle successful registration (e.g., navigate to login page)
                    else:
                        st.error("Registration failed. Please try again.")
                        # Handle errors (e.g., display error message)
                    



    # Assistant Page
    elif page == "Assistant":
        st.header("Smart Dietician Hub")
        question = st.text_input("Enter your question:")
        thread_id = st.text_input("Enter thread id (optional):")

        # Get the user info from the session state
        user_info = st.session_state.user_info if 'user_info' in st.session_state else None 

        if st.button("Submit"):
            response = handle_openai_communication(question, thread_id, user_info)
            print(response)
            st.write(response)
                # Here you can add the code to store these values in your Elasticsearch database

if __name__ == "__main__":
    main()
