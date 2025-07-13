import os
import pytz
import requests
import json
import streamlit as st
import pandas as pd
import datetime as dt
from dotenv import load_dotenv
import openai
from openai import OpenAIError
from utils import (api_call_with_refresh, is_user_authenticated, login_form, 
                   toggle_chef_mode, guest_chat_with_gpt, chat_with_gpt, EventHandler,
                   openai_headers, client, get_user_summary, 
                   resend_activation_link, footer, process_user_input, 
                   fetch_follow_up_recommendations, display_streaming_summary, fetch_and_update_user_profile,
                   check_django_cookies, navigate_to_page)
import numpy as np
import time
import logging
import sys
import uuid

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

# Retrieve the environment variable in Python
django_url = os.getenv("DJANGO_URL")

def show_portion_size_dialog():
    st.markdown("""
    ### Understanding Our Portion Sizes
    When logging your meals, selecting the right portion size helps in accurately tracking your nutritional intake. Here's a guide to what each portion size category represents, making it easier for you to choose when logging meals:

    - **Extra Small (XS):** Ideal for small snacks or condiments. Think of a tablespoon of peanut butter or a small handful of nuts. 🥜

    - **Small (S):** Suitable for side dishes or smaller servings of fruits and vegetables. Imagine a single piece of fruit or half a cup of cooked vegetables. 🍏🥕

    - **Medium (M):** The right size for main components of your meals, like a cup of cooked pasta, a medium-sized chicken breast, or a bowl of salad. 🍝🍗🥗

    - **Large (L):** Fits larger meals and servings, such as a big dinner plate with multiple components or a large smoothie. 🍲🥤

    - **Extra Large (XL):** Reserved for very large or shared meals. Think of a family-sized meal or a large pizza. 🍕👨‍👩‍👧‍👦

    ### How to Use Portion Sizes for Meal Logging

    Using these categories, try to estimate the portion sizes of the meals you're logging. For example:

    - A sandwich with a small side salad might be a **Medium (M)** for the sandwich and **Small (S)** for the salad.
    - A bowl of fruit salad could be **Large (L)** depending on the quantity.

    Remember, these sizes are guidelines to help you in logging your meals more accurately. Depending on your dietary needs, you might adjust the portions. Our goal is to make meal tracking insightful and tailored to your health journey.

    Happy meal logging!
    """)

def calorie_intake_form(selected_date=None):
    # Fetch the user's time zone from session state
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    # Get the current date and time in the user's time zone
    local_date = dt.datetime.now(local_tz).date()

    # Use the provided selected_date or fall back to local_date
    if selected_date is None:
        selected_date = local_date

    with st.form(key='calorie_intake_form'):
        # Date input for the form
        selected_date_input = st.date_input("Date", value=selected_date)
        st.text_input("Meal Name", key='meal_name')
        st.text_area("Meal Description", key='meal_description')

        # Define the portion size choices to match those in your Django model
        portion_size_options = {
            'XS': 'Extra Small',
            'S': 'Small',
            'M': 'Medium',
            'L': 'Large',
            'XL': 'Extra Large',
        }
        
        # Use a selectbox for portion size
        portion_size = st.selectbox(
            "Portion Size", 
            options=list(portion_size_options.keys()), 
            format_func=lambda x: portion_size_options[x], 
            key='portion_size'
        )

        submit_button = st.form_submit_button(label='Submit')
        if submit_button:
            try:
                user_id = st.session_state.get('user_id')
                meal_name = st.session_state['meal_name']
                meal_description = st.session_state['meal_description']
                selected_date_combined = local_tz.localize(dt.datetime.combine(selected_date_input, dt.datetime.min.time()))
                add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date_combined)
            except requests.exceptions.RequestException:
                st.error("Failed to connect to the server. Please try again later.")
            except Exception as e:
                logging.error(f"Error adding calorie intake: {e}")
                st.error("An unexpected error occurred. Please check your inputs and try again.")            

    open_modal_button = st.button("Understand Portion Sizes?", key="open-portion-size-info")
    if open_modal_button:
        show_portion_size_dialog()

def visualize_calorie_data():
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    user_id = st.session_state.get('user_id')

    selected_date = st.date_input("Select Date for Calorie Data", value=dt.datetime.now(local_tz).date())

    calorie_data = fetch_calorie_data(user_id, selected_date)

    if calorie_data:
        df = pd.DataFrame(calorie_data)
        # First localize to UTC (or the appropriate timezone), then convert to the user's timezone
        df['date_recorded'] = pd.to_datetime(df['date_recorded']).dt.tz_localize('UTC').dt.tz_convert(local_tz)

        
        for index, row in df.iterrows():
            st.write(f"Date: {row['date_recorded'].strftime('%Y-%m-%d %H:%M:%S')}, Meal Name: {row['meal_name']}, Meal Description: {row['meal_description']}, Portion Size: {row['portion_size']}")
            edit_button, delete_button = st.columns([0.1, 1])
            with edit_button:
                if st.button("Edit", key=f"edit_{row['id']}"):
                    edit_calorie_record(row['id'])
            with delete_button:
                if st.button("Delete", key=f"delete_{row['id']}"):
                    delete_calorie_record(row['id'])
    else:
        st.info(f"No calorie data recorded for {selected_date.strftime('%Y-%m-%d')}.")

def fetch_user_metrics(user_id):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/health_metrics/',
            method='get',
            headers=headers,
            data={"user_id": user_id}
        )
        if response and response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error("Failed to fetch health metrics")
        logging.error(f"Error fetching health metrics: {e}")
        return []

def metrics():
    user_id = st.session_state.get('user_id')
    metrics_data = fetch_user_metrics(user_id)
    
    # Check if metrics_data is a list and it's not empty
    if isinstance(metrics_data, list) and metrics_data:
        return metrics_data[0]  # Return the first element if available
    else:
        return None  # Return None if no data is available
    

def show_latest_metrics():
    latest_metrics = metrics()

    if latest_metrics:
        weight_display = float(latest_metrics['weight']) if st.session_state['weight_unit'] == 'kg' else np.round(float(latest_metrics['weight']) * 2.20462, 2)
        st.markdown(f"**Latest Weight:** {weight_display} {st.session_state['weight_unit']}")
        st.markdown(f"**Current Mood:** {latest_metrics['mood']}")
        st.markdown(f"**Energy Level:** {latest_metrics['energy_level']}")
    else:
        st.warning("No health metrics available yet.")

def fetch_calorie_data(user_id, selected_date):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/get_calories/',
            method='get',
            headers=headers,
            data={"user_id": user_id, "date": selected_date.strftime('%Y-%m-%d')}
        )
        if response and response.status_code == 200:
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
    except requests.exceptions.RequestException as e:
        st.error("Failed to fetch calorie data")
        logging.error(f"Error fetching calorie data: {e}")
        return []

def edit_calorie_record(record_id):
    user_id = st.session_state.get('user_id')
    record_data = fetch_calorie_data(record_id)

    # Define the portion size choices to match those in your Django model
    portion_size_options = {
        'XS': 'Extra Small',
        'S': 'Small',
        'M': 'Medium',
        'L': 'Large',
        'XL': 'Extra Large',
    }

    if record_data:
        with st.form(key='edit_calorie_form'):
            new_date = st.date_input("Date", value=pd.to_datetime(record_data['date_recorded']).date())
            new_meal_name = st.text_input("Meal Name", value=record_data['meal_name'])
            new_meal_description = st.text_area("Meal Description", value=record_data['meal_description'])
            
            # Use a selectbox for portion size instead of text input
            # Convert the stored portion size value back to its descriptive form for the selectbox default value
            new_portion_size = st.selectbox("Portion Size", options=list(portion_size_options.keys()), format_func=lambda x: portion_size_options[x], index=list(portion_size_options.keys()).index(record_data['portion_size']))
            
            submit_button = st.form_submit_button("Save Changes")

            if submit_button:
                update_payload = {
                    "meal_name": new_meal_name,  # Use the new meal name
                    "meal_description": new_meal_description,
                    "portion_size": new_portion_size,  # Save the key of the selected portion size
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
                    st.rerun()  # Refresh data
                else:
                    st.error("Failed to update calorie record")

def delete_calorie_record(record_id):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    try:
        response = requests.delete(
            f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/delete_calorie_intake/{record_id}/',
            headers=headers
        )
        if response and response.status_code == 204:
            st.success("Calorie record deleted successfully")
        st.rerun()
    except requests.exceptions.RequestException as e:
        st.error("Failed to delete calorie record")
        logging.error(f"Error deleting calorie record: {e}")

def add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    # Format the date as a string
    formatted_date = selected_date.strftime('%Y-%m-%d')
    payload = {
        "user_id": user_id,
        "meal_name": meal_name,
        "meal_description": meal_description,
        "portion_size": portion_size,
        "date_recorded": formatted_date ,
    }

    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/add_calories/',
            method='post',
            data=payload,
            headers=headers
        )
        if response and response.status_code == 201:
            st.success("Calorie intake added successfully!")
        else:
            st.error(f"Failed to add calorie intake: {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add calorie intake: {response.text}")
        logging.error(f"Error adding calorie intake: {e}")

def save_health_metrics(date, weight, mood, energy_level):
    user_id = st.session_state.get('user_id')
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    # Format the date as a string
    formatted_date = date.strftime('%Y-%m-%d')

    payload = {
        "id": user_id,
        "date_recorded": formatted_date,  # Use the formatted string
        "weight": weight,
        "mood": mood,
        "energy_level": energy_level
    }
    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/health_metrics/',
            method='post',
            data=payload,
            headers=headers
        )
        if response and response.status_code == 200:
            st.success("Health metrics updated!")
    except requests.exceptions.RequestException as e:
        st.error("Failed to update health metrics")
        logging.error(f"Error updating health metrics: {e}")

def visualize_health_metrics_as_static_table():
    # Allow users to select their preferred weight unit
    weight_unit = st.radio("Select Weight Unit", ('kg', 'lbs'))
    st.session_state['weight_unit'] = weight_unit

    user_id = st.session_state.get('user_id')
    health_metrics = fetch_user_metrics(user_id)

    if isinstance(health_metrics, list) and health_metrics:
        df = pd.DataFrame(health_metrics)

        # Ensure the weight column is numeric, converting if necessary
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce')

        # Convert the weight to the selected unit and format to two decimal places
        if st.session_state['weight_unit'] == 'lbs':
            df['weight'] = df['weight'].apply(lambda x: f"{x * 2.20462:.2f}")
        else:
            df['weight'] = df['weight'].apply(lambda x: f"{x:.2f}")

        # Pagination
        items_per_page = 10  # You can adjust this value
        if 'page_number' not in st.session_state:
            st.session_state.page_number = 0
        page_number = st.session_state.page_number
        start_index = page_number * items_per_page
        end_index = start_index + items_per_page
        paginated_df = df.iloc[start_index:end_index]

        st.table(paginated_df[['date_recorded', 'weight', 'mood', 'energy_level']])

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

    if not filtered_df.empty and not filtered_df[metric_name].isna().all():
        st.subheader(f"{metric_name.capitalize()} Trend")
        st.line_chart(filtered_df[metric_name])
    else:
        st.warning(f"No data available for {metric_name} in the selected date range. Please check if the data exists for this range.")

def plot_metric_trends(metric_trends):
    if metric_trends and isinstance(metric_trends, list) and isinstance(metric_trends[0], dict):
        df = pd.DataFrame(metric_trends)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
        df['date'] = pd.to_datetime(df['date_recorded']).dt.normalize()
        df.set_index('date', inplace=True)

        min_date, max_date = df.index.min(), df.index.max()
        
        st.write("### Select Date Range for Visualization")
        start_date = st.date_input("Start Date", value=min_date)
        end_date = st.date_input("End Date", value=max_date)

        if start_date > end_date:
            st.error("Start Date must be before End Date")
        else:
            selected_range = (start_date, end_date)
            plot_metric_trend('weight', df, selected_range)
            plot_metric_trend('energy_level', df, selected_range)
    else:
        st.warning("No metric trends available to display.")

def health_metrics_form():
    # Add a session state variable for weight unit if not present
    if 'weight_unit' not in st.session_state:
        st.session_state['weight_unit'] = 'kg'  # default unit
        
    # Fetch the user's time zone from session state
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    weight_unit = st.radio("Weight Unit", ('kg', 'lbs'))
    st.session_state['weight_unit'] = weight_unit

    with st.form(key='health_metrics_form'):
        # Convert current date to user's time zone
        local_date = dt.datetime.now(local_tz).date()
        date_input = st.date_input("Date", value=local_date)
        weight_input = st.number_input(f"Weight ({st.session_state['weight_unit']})", min_value=0.0, format="%.2f")
        weight = weight_input if st.session_state['weight_unit'] == 'kg' else np.round(weight_input / 2.20462, 2)
        mood = st.selectbox("Mood", ["Happy", "Sad", "Stressed", "Relaxed", "Energetic", "Tired", "Neutral"])
        energy_level = st.slider("Energy Level", 1, 10, 5)

        submit_button = st.form_submit_button(label='Submit')
        if submit_button:
            try: 
                weight = weight if weight != 0.0 else None
                date_to_save = local_tz.localize(dt.datetime.combine(date_input, dt.datetime.min.time()))  # Localize to user's timezone
                save_health_metrics(date_to_save, weight, mood, energy_level)
            except requests.exceptions.RequestException:
                st.error("Failed to connect to the server. Please try again later.")
            except Exception as e:
                logging.error(f"Error adding calorie intake: {e}")
                st.error("An unexpected error occurred. Please check your inputs and try again.")

# Main application code
try:
    # Handle email authentication link
    _params = st.query_params
    _auth_token_full_list = _params.get("auth_token")
    _expected_action_suffix = _params.get("action")

    if _auth_token_full_list:
        

        
        # Check if the action is appended to the auth_token query parameter value
        if _auth_token_full_list and _expected_action_suffix == "email_auth":
            _actual_auth_token = _auth_token_full_list.split(_expected_action_suffix)[0]

            # Clear query params immediately to prevent re-processing and clean up URL
            st.query_params.clear() # Clears all query params

            if _actual_auth_token:
                api_url = f'{os.getenv("DJANGO_URL")}/auth/api/email_auth/{_actual_auth_token}/'
                try:
                    # This is a public endpoint, no auth headers needed for the call itself
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        st.success("Email confirmed successfully! You can communicate with your personal assistant now via email.")
                    else:
                        error_message = "Failed to confirm email. The link may be invalid or expired."
                        try:
                            error_details = response.json()

                            # Prioritize 'detail' or 'message' over 'status'
                            if "detail" in error_details:
                                error_message = error_details["detail"]
                            elif "message" in error_details:
                                error_message = error_details["message"]
                            elif "status" in error_details:
                                # Only show status if it's NOT just 'error'
                                status_val = error_details["status"]
                                if status_val != "error":
                                    error_message = status_val
                                # Otherwise, keep default/fallback
                            else:
                                # Show the full dict if nothing matches (debugging)
                                error_message = str(error_details)

                        except requests.exceptions.JSONDecodeError:
                            pass

                        st.warning(error_message)
                        # No explicit st.stop() here, use switch_page
                        navigate_to_page('home')
                except requests.exceptions.RequestException as e:
                    logging.error(f"Email auth request exception: {str(e)}")
                    st.error(f"An error occurred while trying to confirm your email. Please check your connection and try again.")
                    # No explicit st.stop() here, use switch_page
                    navigate_to_page('home')


    # Initialize session state variables if not already initialized
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None
    if 'recommend_follow_up' not in st.session_state:
        st.session_state.recommend_follow_up = []
    if 'showed_user_summary' not in st.session_state:
        st.session_state.showed_user_summary = False
    if 'recommend_prompt' not in st.session_state:
        st.session_state.recommend_prompt = ""

    # Login Form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        login_form()

    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='form_logout'):
            # Clear session state but preserve navigation
            navigation_state = st.session_state.get("navigation", None)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            if navigation_state:
                st.session_state["navigation"] = navigation_state
            st.success("Logged out successfully!")
            st.rerun()

    # Check if the user is authenticated and email is confirmed
    if is_user_authenticated() and st.session_state.get('email_confirmed', False):
        # Additional functionalities for authenticated users not in chef mode
        if st.session_state.get('current_role', '') != 'chef':
            with st.expander("Calorie Intake and Data", expanded=False):
                # Row 1: Calorie Intake Form
                st.subheader("Calorie Intake")
                calorie_intake_form(dt.date.today())
                st.markdown("---")  # Separator for better readability

                # Row 2: Calorie Data Visualization
                st.subheader("Calorie Visualization")
                visualize_calorie_data()

            with st.expander("Health Metrics", expanded=False):
                # Row 3: Health Metrics Form
                st.subheader("Health Metrics Input")
                health_metrics_form()
                st.markdown("---")  # Separator for better readability

                # Row 4: Health Metrics Visualization
                st.subheader("Health Metrics Visualization")
                viz_type = st.selectbox("Choose visualization type", ["Static Table", "Latest Metrics", "Trend Chart"])
                if viz_type == "Static Table":
                    visualize_health_metrics_as_static_table()
                elif viz_type == "Latest Metrics":
                    show_latest_metrics()
                elif viz_type == "Trend Chart":
                    user_id = st.session_state.get('user_id')
                    metric_trends = fetch_user_metrics(user_id)
                    plot_metric_trends(metric_trends)

        # --- DAILY SUMMARY (streaming) ------------------------------------------
        if (
            is_user_authenticated()
            and st.session_state.get('current_role', '') != 'chef'
            and not st.session_state.get('showed_user_summary', False)
        ):
            with st.spinner("Streaming your daily summary…"):
                summary_data = display_streaming_summary()   # generator → writes itself

            if summary_data and summary_data.get("summary"):
                # Push into chat so it scrolls naturally
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": summary_data["summary"]
                })
                # Keep recommendations if backend sent them
                st.session_state.recommend_follow_up = summary_data.get("recommend_prompt", {})
            else:
                st.warning("Summary wasn't available yet – you can still chat normally.")

            # prevent re-fetch on rerun
            st.session_state.showed_user_summary = True
        # ------------------------------------------------------------------------

    # If email is not confirmed, restrict access and prompt to resend activation link
    elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
        st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
        if st.button("Resend Activation Link"):
            resend_activation_link(st.session_state['user_id'])
            st.rerun()

    # Check if a thread was selected in history
    if 'selected_thread_id' in st.session_state and st.session_state.selected_thread_id not in [None, '']:
        thread_id = st.session_state.selected_thread_id
        st.session_state.thread_id = thread_id
        st.session_state.chat_history = []

        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/thread_detail/{thread_id}/',
            method='get',
            headers=headers
        )
        if response.status_code == 200:
            chat_history = response.json().get('chat_history', [])
            if chat_history:
                # Sort by created timestamp
                chat_history.sort(key=lambda x: x['created_at'])

                for msg in chat_history:
                    st.session_state.chat_history.append({"role": msg['role'], "content": msg['content']})
            else:
                logging.error("No chat history found for selected thread.")
        else:
            st.error("Error fetching thread details.")
            logging.error(f"Error fetching thread details: {response.status_code}, {response.text}")

    # Set up the chat container
    st.title("Chat with SautAI")
    chat_container = st.container()

    # Keep the chat input visible by fixing it to the bottom
    st.markdown(
        """
        <style>
        [data-testid="stChatInput"] {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 100;
        }

        [data-testid="stChatInput"] textarea {
            border: 2px solid var(--primary-color);
            box-shadow: 0 0 10px var(--primary-color);
            animation: sautai-glow 2s ease-in-out infinite alternate;
        }

        @keyframes sautai-glow {
            from { box-shadow: 0 0 5px var(--primary-color); }
            to { box-shadow: 0 0 15px var(--primary-color); }
        }

        .appview-container .main .block-container {
            padding-bottom: 6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Use a container to dynamically update chat messages
    st.info("Response time may vary. Your patience is appreciated.")

    # Chat functionality available to unauthenticated users or authenticated non-chef users
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in'] or (st.session_state.get('current_role', '') != 'chef'):
        # Process and display chat interactions
        for message in st.session_state.chat_history:
            with chat_container.chat_message(message["role"]):
                # Detect whether the backend returned structured JSON containing an HTML payment button
                content = message["content"]
                parsed = None
                if isinstance(content, dict):
                    parsed = content
                else:
                    try:
                        parsed = json.loads(content)
                    except (TypeError, ValueError):
                        pass

                if parsed and isinstance(parsed, dict) and parsed.get("html_button"):
                    # Render the checkout button (unsafe HTML allowed for anchor tags/div styling)
                    st.markdown(parsed["html_button"], unsafe_allow_html=True)
                else:
                    st.markdown(content)

        # Display follow-up recommendations if available (only for non-chef users)
        raw_followups = st.session_state.get('recommend_follow_up', [])
        if isinstance(raw_followups, dict):
            items = raw_followups.get('items', [])
        elif isinstance(raw_followups, list):
            items = raw_followups
        else:
            items = []

        if items and st.session_state.get('current_role', '') != 'chef':
            with st.expander("Recommended Follow‑Ups", expanded=False, icon="💡"):
                for idx, item in enumerate(items):
                    text = item.get('recommendation', '')
                    if st.button(text, key=f"{text}_{idx}"):
                        process_user_input(text, chat_container)
        else:
            logging.info("No follow‑up recommendations to display.")

        # Get user input
        prompt = st.chat_input("Enter your question:")
        if prompt:
            process_user_input(prompt, chat_container)

        # Button to start a new chat
        if st.session_state.chat_history and st.button("Start New Chat"):
            try:
                if is_user_authenticated():
                    # Authenticated user: Call new_conversation endpoint
                    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    response = api_call_with_refresh(
                        url=f'{django_url}/customer_dashboard/api/assistant/new-conversation/',
                        method='post',
                        headers=headers
                    )
                    if response and response.status_code == 200:
                        st.session_state.thread_id = None
                        st.session_state.chat_history = []
                        st.session_state.selected_thread_id = None
                        st.session_state.recommend_follow_up = []
                        st.session_state.showed_user_summary = False # Reset summary flag
                        chat_container.empty()
                        st.rerun()
                    else:
                        st.error("Failed to start a new conversation. Please try again.")
                        logging.error(f"Failed to start new conversation. Status: {response.status_code if response else 'No Response'}, Body: {response.text if response else 'N/A'}")
                else:
                    # Guest user: Call guest_new_conversation endpoint
                    guest_session_data = {}
                    if 'guest_id' in st.session_state:
                         guest_session_data['guest_id'] = st.session_state['guest_id'] # Send old guest_id if available

                    response = requests.post(
                        url=f'{django_url}/customer_dashboard/api/assistant/guest-new-conversation/',
                        json=guest_session_data # Send empty JSON or guest_id if available
                    )
                    if response.status_code == 200:
                        new_guest_id = response.json().get('guest_id')
                        if new_guest_id:
                            st.session_state['guest_id'] = new_guest_id # Update session with new guest ID
                        else:
                             logging.error("Guest new conversation endpoint did not return a new guest_id.")
                             # Decide if this is a critical error or can proceed without new ID

                        st.session_state.thread_id = None
                        st.session_state.chat_history = []
                        st.session_state.selected_thread_id = None
                        st.session_state.recommend_follow_up = []
                        chat_container.empty()
                        st.rerun()
                    else:
                        st.error("Failed to start a new guest conversation. Please try again.")
                        logging.error(f"Failed to start new guest conversation. Status: {response.status_code}, Body: {response.text}")

            except requests.exceptions.RequestException as e:
                st.error("Connection error starting new chat. Please check your connection and try again.")
                logging.error(f"Connection error starting new chat: {e}")
            except Exception as e:
                st.error("An unexpected error occurred while starting a new chat.")
                logging.error("Unexpected error starting new chat", exc_info=True)
    else:
        # For chef mode users, show a simplified chat interface
        # TODO: Add a chef mode chat interface with a backend api for chef specific queries and tools
        st.info("You are currently in Chef Mode. Some features may be limited.")
        for message in st.session_state.chat_history:
            with chat_container.chat_message(message["role"]):
                content = message["content"]
                parsed = None
                if isinstance(content, dict):
                    parsed = content
                else:
                    try:
                        parsed = json.loads(content)
                    except (TypeError, ValueError):
                        pass

                if parsed and isinstance(parsed, dict) and parsed.get("html_button"):
                    st.markdown(parsed["html_button"], unsafe_allow_html=True)
                else:
                    st.markdown(content)

        # Get user input
        prompt = st.chat_input("Enter your question:")
        if prompt:
            process_user_input(prompt, chat_container)

        # Button to start a new chat (Chef Mode)
        if st.session_state.chat_history and st.button("Start New Chat"):
            # For Chef mode, we might need a separate logic or endpoint,
            # or perhaps Chefs always use the authenticated endpoint.
            # Assuming Chef is an authenticated user for now.
            try:
                if is_user_authenticated(): # Assuming chefs are always authenticated
                    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    response = api_call_with_refresh(
                        url=f'{django_url}/customer_dashboard/api/assistant/new-conversation/',
                        method='post',
                        headers=headers
                    )
                    if response and response.status_code == 200:
                        st.session_state.thread_id = None
                        st.session_state.chat_history = []
                        st.session_state.selected_thread_id = None
                        # No recommend_follow_up or summary for chefs typically
                        chat_container.empty()
                        st.rerun()
                    else:
                        st.error("Failed to start a new conversation. Please try again.")
                        logging.error(f"Failed to start new conversation (Chef Mode). Status: {response.status_code if response else 'No Response'}, Body: {response.text if response else 'N/A'}")
                else:
                     # This case should ideally not happen if Chefs must be authenticated
                     st.error("Error: Chef user not authenticated.")
                     logging.error("Chef mode 'Start New Chat' attempted without authentication.")

            except requests.exceptions.RequestException as e:
                st.error("Connection error starting new chat. Please check your connection and try again.")
                logging.error(f"Connection error starting new chat (Chef Mode): {e}")
            except Exception as e:
                st.error("An unexpected error occurred while starting a new chat.")
                logging.error("Unexpected error starting new chat (Chef Mode)", exc_info=True)

except Exception as e:
    logging.error("Exception occurred", exc_info=True)
    st.error("An unexpected error occurred. Please try again later.")

st.markdown(
    """
    <a href="https://www.buymeacoffee.com/sautai" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px; width: 217px;" >
    </a>
    """,
    unsafe_allow_html=True
)

footer()
