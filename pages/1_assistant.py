import os
import requests
import json
import streamlit as st
import pandas as pd
import datetime
from dotenv import load_dotenv
import openai
from openai import OpenAIError
from utils import api_call_with_refresh, is_user_authenticated
import streamlit.components.v1 as components
import numpy as np

load_dotenv()



# Retrieve the environment variable in Python
django_url = os.getenv("DJANGO_URL")

openai_env_key = os.getenv("OPENAI_KEY")

if openai_env_key:
    openai.api_key = openai_env_key

client = openai

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="expanded",
    menu_items={
        'Report a bug': "mailto:support@sautai.com",
        'About': """
        # Welcome to sautAI 🥗
        
        **sautAI** is your personal diet and nutrition assistant, designed to empower you towards achieving your health and wellness goals. Here's what makes sautAI special:

        - **Diverse Meal Discoveries**: Explore a vast database of dishes and meet talented chefs. Whether you're craving something specific or looking for inspiration, sautAI connects you with the perfect meal solutions.
        
        - **Customized Meal Planning**: Get personalized weekly meal plans that cater to your dietary preferences and nutritional needs. With sautAI, planning your meals has never been easier or more exciting.
        
        - **Ingredient Insights**: Navigate dietary restrictions with ease. Search for meals by ingredients or exclude specific ones to meet your dietary needs.
        
        - **Interactive Meal Management**: Customize your meal plans by adding, removing, or replacing meals. sautAI makes it simple to adjust your plan on the fly.
        
        - **Feedback & Reviews**: Share your culinary experiences and read what others have to say. Your feedback helps us refine and enhance the sautAI experience.
        
        - **Health & Wellness Tracking**: Monitor your health metrics, set and update goals, and receive tailored nutrition advice. sautAI is here to support your journey towards a healthier lifestyle.
        
        - **Local Supermarket Finder**: Discover supermarkets near you offering healthy meal options. Eating healthy is now more convenient than ever.
        
        - **Allergy & Dietary Alerts**: Stay informed about potential allergens in your meals. sautAI prioritizes your health and safety.
        
        Discover the joy of healthy eating and seamless meal planning with **sautAI**. Let's embark on this journey together.

        ### Stay Connected
        Have questions or feedback? Contact us at [support@sautai.com](mailto:support@sautai.com).

        Follow us on our journey:
        - [Instagram](@sautAI_official)
        - [Twitter](@sautAI_official)
        - [Report a Bug](mailto:support@sautai.com)
        """
    }
)

def fetch_user_metrics(user_id):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(
        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/health_metrics/',
        method='get',
        headers=headers, data={"user_id": user_id}
    )

    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch health metrics")
        return []


def metrics():
    user_id = st.session_state.get('user_id')
    metrics_data = fetch_user_metrics(user_id)
    
    # Check if metrics_data is not empty
    if metrics_data:
        return metrics_data[0]  # Return the first element if available
    else:
        return None  # Return None if no data is available
    

def show_latest_metrics():
    latest_metrics = metrics()

    if latest_metrics:
        weight_display = float(latest_metrics['weight']) if st.session_state['weight_unit'] == 'kg' else np.round(float(latest_metrics['weight']) * 2.20462, 2)
        st.markdown(f"**Latest Weight:** {weight_display} {st.session_state['weight_unit']}")
        st.markdown(f"**Latest BMI:** {latest_metrics['bmi']}")
        st.markdown(f"**Current Mood:** {latest_metrics['mood']}")
        st.markdown(f"**Energy Level:** {latest_metrics['energy_level']}")
    else:
        st.warning("No health metrics available yet.")

def fetch_calorie_data(user_id, selected_date):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(
        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/get_calories/',
        method='get',
        headers=headers,
        data={"user_id": user_id, "date": selected_date.strftime('%Y-%m-%d')}
    )

    if response.status_code == 200:
        calorie_data = response.json()
        if calorie_data:  # Check if data is not empty
            return calorie_data
        else:
            # Return a specific value or message indicating no data
            st.info("No calorie data recorded yet.")  # Informative message for the user
            return []
    else:
        st.error("Failed to fetch calorie data")
        return []
    
def edit_calorie_record(record_id):
    user_id = st.session_state.get('user_id')
    record_data = fetch_calorie_data(record_id)

    if record_data:
        with st.form(key='edit_calorie_form'):
            new_date = st.date_input("Date", value=pd.to_datetime(record_data['date_recorded']).date())
            new_meal_name = st.text_input("Meal Name", value=record_data['meal_name'])
            new_meal_description = st.text_area("Meal Description", value=record_data['meal_description'])
            new_portion_size = st.text_input("Portion Size", value=record_data['portion_size'])
            submit_button = st.form_submit_button("Save Changes")

            if submit_button:
                update_payload = {
                    "meal_name": new_meal_name,  # Use the new meal name
                    "meal_description": new_meal_description,
                    "portion_size": new_portion_size,
                    "date_recorded": new_date.strftime('%Y-%m-%d')
                }
                update_response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/api/calorie_intake/{record_id}/',
                    method='put',
                    data=update_payload,
                    headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                )
                if update_response.status_code == 200:
                    st.success("Calorie record updated successfully!")
                    st.experimental_rerun()  # Refresh data
                else:
                    st.error("Failed to update calorie record")

def delete_calorie_record(record_id):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = requests.delete(
        f'{os.getenv("DJANGO_URL")}/api/delete_calorie_intake/{record_id}/',
        headers=headers
    )
    if response.status_code == 200:
        st.success("Calorie record deleted successfully")
        st.experimental_rerun() 
    else:
        st.error("Failed to delete calorie record")

def add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    payload = {
        "user_id": user_id,
        "meal_name": meal_name,
        "meal_description": meal_description,
        "portion_size": portion_size,
        "date_recorded": selected_date.strftime('%Y-%m-%d'),
    }

    response = api_call_with_refresh(
        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/add_calories/',
        method='post',
        data=payload,
        headers=headers
    )

    if response.status_code == 201:
        st.success("Calorie intake added successfully!")
    else:
        st.error(f"Failed to add calorie intake: {response.text}")

def calorie_intake_form(selected_date):
    with st.sidebar:
        with st.expander("Calorie Intake", expanded=True):
            with st.form(key='calorie_intake_form'):
                st.date_input("Date", value=selected_date, key='calorie_date')
                st.text_input("Meal Name", key='meal_name')
                st.text_area("Meal Description", key='meal_description')
                st.text_input("Portion Size", key='portion_size')
                submit_button = st.form_submit_button(label='Submit')
                if submit_button:
                    user_id = st.session_state.get('user_id')
                    # Retrieving the values
                    meal_name = st.session_state['meal_name']
                    meal_description = st.session_state['meal_description']
                    portion_size = st.session_state['portion_size']
                    selected_date = st.session_state['calorie_date']
                    add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date)


def visualize_calorie_data(selected_date):
    user_id = st.session_state.get('user_id')
    calorie_data = fetch_calorie_data(user_id, selected_date)

    if calorie_data:
        df = pd.DataFrame(calorie_data)
        # Implement pagination if needed
        for index, row in df.iterrows():
            st.write(f"Date: {row['date_recorded']}, Meal Name: {row['meal_name']}, Meal Description: {row['meal_description']}, Portion Size: {row['portion_size']}")
            edit_button, delete_button = st.columns([0.1, 1])
            with edit_button:
                if st.button("Edit", key=f"edit_{row['id']}"):
                    # Call the edit function with the record ID
                    edit_calorie_record(row['id'])
            with delete_button:
                if st.button("Delete", key=f"delete_{row['id']}"):
                    delete_calorie_record(row['id'])
    else:
        st.info(f"No calorie data recorded for {selected_date.strftime('%Y-%m-%d')}.")


def save_health_metrics(date, weight, bmi, mood, energy_level):
    user_id = st.session_state.get('user_id')
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    # Format the date as a string
    formatted_date = date.strftime('%Y-%m-%d')

    payload = {
        "id": user_id,
        "date_recorded": formatted_date,  # Use the formatted string
        "weight": weight,
        "bmi": bmi,
        "mood": mood,
        "energy_level": energy_level
    }

    response = api_call_with_refresh(
        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/health_metrics/',
        method='post',
        data=payload,
        headers=headers
    )

    if response.status_code == 200:
        st.success("Health metrics updated!")
    else:
        st.error(f"Failed to save health metrics: {response.text}")

def plot_metric_trends():
    user_id = st.session_state.get('user_id')
    metric_trends = fetch_user_metrics(user_id)
    
    if metric_trends:
        # Original data
        df = pd.DataFrame(metric_trends)
        df['date'] = pd.to_datetime(df['date_recorded'])
        df.set_index('date', inplace=True)

        # Full range dates DataFrame
        all_dates = pd.date_range(df.index.min(), df.index.max(), freq='D')
        df_full = pd.DataFrame(index=all_dates)
        
        # Joining the full dates DataFrame with the original data
        # Dates without data in the original DataFrame will have NaN values after the join
        df_full = df_full.join(df, how='left')

        min_date, max_date = df_full.index.min(), df_full.index.max()

        # User selects a date range for visualization
        selected_range = st.select_slider(
            "Select Date Range", 
            options=pd.date_range(min_date, max_date, freq='D'),
            value=(min_date, max_date)
        )

        # Filter the DataFrame based on the selected date range
        filtered_df = df_full.loc[selected_range[0]:selected_range[1]]

        # Plotting the chart with filtered DataFrame
        # The chart will show gaps where the data is NaN (not available for certain dates)
        st.line_chart(filtered_df[['weight', 'bmi', 'energy_level']])
    else:
        st.error("No metric trends available to display.")

def visualize_health_metrics_as_static_table():
    user_id = st.session_state.get('user_id')
    health_metrics = fetch_user_metrics(user_id)

    if isinstance(health_metrics, list) and health_metrics:
        df = pd.DataFrame(health_metrics)

        # Pagination
        items_per_page = 10  # You can adjust this value
        if 'page_number' not in st.session_state:
            st.session_state.page_number = 0
        page_number = st.session_state.page_number
        start_index = page_number * items_per_page
        end_index = start_index + items_per_page
        paginated_df = df.iloc[start_index:end_index]

        st.table(paginated_df[['date_recorded', 'weight', 'bmi', 'mood', 'energy_level']])

        # Page navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Previous'):
                if st.session_state.page_number > 0:
                    st.session_state.page_number -= 1
        with col2:
            if st.button('Next'):
                if end_index < len(df):
                    st.session_state.page_number += 1
    else:
        st.info("No health metrics data available to display.")

def plot_metric_trend(metric_name, df, selected_range):
    """
    Plot the trend for a specific metric over a selected date range.
    """
    # Convert selected range into a list of dates
    date_list = pd.date_range(start=selected_range[0], end=selected_range[1]).date.tolist()
    
    # Filter the DataFrame based on the list of dates
    filtered_df = df[df.index.isin(date_list)]

    # Debugging: Print the filtered DataFrame

    if not filtered_df.empty and not filtered_df[metric_name].isna().all():
        st.subheader(f"{metric_name.capitalize()} Trend")
        st.line_chart(filtered_df[metric_name])
    else:
        st.warning(f"No data available for {metric_name} in the selected date range. Please check if the data exists for this range.")


def plot_metric_trends(metric_trends):
    """
    Plot trends for weight, BMI, and energy level.
    """
    if metric_trends:
        df = pd.DataFrame(metric_trends)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
        df['bmi'] = pd.to_numeric(df['bmi'], errors='coerce')
        df['date'] = pd.to_datetime(df['date_recorded']).dt.normalize()  # Normalize to remove time component
        df.set_index('date', inplace=True)

        min_date, max_date = df.index.min(), df.index.max()

        selected_range = st.select_slider(
            "Select Date Range", 
            options=pd.date_range(min_date, max_date, freq='D'),
            value=(min_date, max_date)
        )

        plot_metric_trend('weight', df, selected_range)
        plot_metric_trend('bmi', df, selected_range)
        plot_metric_trend('energy_level', df, selected_range)
    else:
        st.error("No metric trends available to display.")

def health_metrics_form():
    # Add a session state variable for weight unit if not present
    if 'weight_unit' not in st.session_state:
        st.session_state['weight_unit'] = 'kg'  # default unit

    with st.sidebar.expander("Health Metrics", expanded=False):  # Set expanded to False
        # Toggle for weight unit
        weight_unit = st.radio("Weight Unit", ('kg', 'lbs'))

        # Update the session state variable
        st.session_state['weight_unit'] = weight_unit

        with st.form(key='health_metrics_form'):
            date = st.date_input("Date", value=datetime.date.today())
            weight_input = st.number_input(f"Weight ({st.session_state['weight_unit']})", min_value=0.0, format="%.2f")
            # Convert lbs to kg if necessary
            weight = weight_input if st.session_state['weight_unit'] == 'kg' else np.round(weight_input / 2.20462, 2)
            bmi = st.number_input("BMI", min_value=0.0, format="%.2f")
            mood = st.selectbox("Mood", ["Happy", "Sad", "Stressed", "Relaxed", "Energetic", "Tired", "Neutral"])
            energy_level = st.slider("Energy Level", 1, 10, 5)

            submit_button = st.form_submit_button(label='Submit')
            if submit_button:
                # If no input is made, the value will be None
                weight = weight if weight != 0.0 else None
                bmi = bmi if bmi != 0.0 else None
                save_health_metrics(date, weight, bmi, mood, energy_level)

def guest_chat_with_gpt(prompt, thread_id):
    response_data = requests.post(
        f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/guest_chat_with_gpt/', 
        data={'question': prompt, 'thread_id': thread_id}
    )
    if response_data.status_code == 200:
        return response_data.json()
    if response_data.status_code == 429:  # Rate limit status code
        st.error("You've exceeded the rate limit. Please try again later or consider registering.")
    else:
        st.error("Failed to get response from the chatbot.")
        return None

def chat_with_gpt(prompt, thread_id, user_id):
    response_data = requests.post(
        f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/chat_with_gpt/', 
        data={'question': prompt, 'thread_id': thread_id, 'user_id': user_id}
    )
    if response_data.status_code == 200:
        print('response_data.json():', response_data.json())
        return response_data.json()
    else:
        st.error("Failed to get response from the chatbot.")
        return None

def assistant():
    st.title("Dietician Assistant")

    # Login Form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        with st.expander("Login", expanded=False):
            st.write("Login to your account.")
            with st.form(key='login_form'):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit_button = st.form_submit_button(label='Login')
                register_button = st.form_submit_button(label="Register")

            if submit_button:
                # Remove guest user from session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # API call to get the token
                response = requests.post(
                    f'{os.getenv("DJANGO_URL")}/auth/api/login/',
                    json={'username': username, 'password': password}
                )
                print(response)
                if response.status_code == 200:
                    response_data = response.json()
                    st.success("Logged in successfully!")
                    st.session_state['user_info'] = response_data
                    st.session_state['user_id'] = response_data['user_id']
                    st.session_state['email_confirmed'] = response_data['email_confirmed']
                    # Set cookie with the access token
                    st.session_state['access_token'] = response_data['access']
                    # Set cookie with the refresh token
                    st.session_state['refresh_token'] = response_data['refresh']
                    expires_at = datetime.datetime.now() + datetime.timedelta(days=1)
                    st.session_state['is_logged_in'] = True
                    st.switch_page("pages/1_assistant.py")
                else:
                    st.error("Invalid username or password.")
            if register_button:
                st.switch_page("pages/5_register.py")
                    

            # Password Reset Button
            if st.button("Forgot your password?"):
                # Directly navigate to the activate page for password reset
                st.switch_page("pages/4_account.py")

    # Initialize session state variables if not already initialized
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None
    if 'recommend_follow_up' not in st.session_state:
        st.session_state.recommend_follow_up = []


    # Function to handle follow-up prompt click
    def on_follow_up_click(follow_up_prompt):
        # Update chat history immediately with the follow-up prompt
        st.session_state.chat_history.append({"role": "user", "content": follow_up_prompt})
        # Process the follow-up prompt immediately
        process_user_input(follow_up_prompt)
        # Clear recommend_follow_up from session state
        st.session_state.recommend_follow_up = []

    # Function to process and display user input
    def process_user_input(prompt):
        with chat_container.chat_message("user"):
            st.markdown(prompt)
        thread_id = st.session_state.thread_id 
        # Process the question and get response
        # full_response = handle_openai_communication(prompt, thread_id, {"user_id": st.session_state.get('user_id')})
        # Interaction with the chat_with_gpt endpoint
        if is_user_authenticated():
            full_response = chat_with_gpt(prompt, thread_id, user_id=st.session_state.get('user_id'))
        else:
            full_response = guest_chat_with_gpt(prompt, thread_id)
        print('full_response:', full_response)
        if full_response:
            st.session_state.thread_id = full_response['new_thread_id']
            st.session_state.recommend_follow_up = full_response['recommend_follow_up']
            print("Debug: recommend_follow_up set to:", st.session_state.recommend_follow_up)  # Debug print
            st.session_state.chat_history.append({"role": "assistant", "content": full_response['last_assistant_message']})
            # Dynamically update the chat container
            with chat_container.chat_message("assistant"):
                st.markdown(full_response['last_assistant_message'])

        else:
            st.error("Could not get a response, please try again.")


    if is_user_authenticated():
        # Calorie Intake Form in the Sidebar
        calorie_intake_form(datetime.date.today())

        # Calorie Data Visualization
        with st.expander("View Calorie Data", expanded=False):
            selected_date = st.date_input("Select a date", datetime.date.today())
            visualize_calorie_data(selected_date)

        with st.expander("Health Metrics", expanded=False):
            health_metrics_form()
            viz_type = st.selectbox("Choose visualization type", ["Static Table", "Latest Metrics", "Trend Chart"])
            if viz_type == "Static Table":
                visualize_health_metrics_as_static_table()
            elif viz_type == "Latest Metrics":
                show_latest_metrics()
            elif viz_type == "Trend Chart":
                user_id = st.session_state.get('user_id')
                metric_trends = fetch_user_metrics(user_id)
                plot_metric_trends(metric_trends)

    # Use a container to dynamically update chat messages
    chat_container = st.container(height=400)

    # Display chat history
    for message in st.session_state.chat_history:
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])

    # Display recommended follow-up prompts
    if st.session_state.recommend_follow_up:
        with st.container():
            st.write("Recommended Follow-Ups:")
            for follow_up in st.session_state.recommend_follow_up:
                st.button(follow_up, key=follow_up, on_click=on_follow_up_click, args=(follow_up,))

    # Chat input for user questions
    prompt = st.chat_input("Enter your question:")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        process_user_input(prompt)
        st.rerun()

    # Button to start a new chat
    if st.session_state.chat_history and st.button("Start New Chat"):
        st.session_state.thread_id = None
        st.session_state.chat_history = []
        st.session_state.recommend_follow_up = []
        chat_container.empty()
        st.rerun()



if __name__ == "__main__":
    assistant()
