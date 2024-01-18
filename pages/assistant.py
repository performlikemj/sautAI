import os
import requests
import json
import streamlit as st
import pandas as pd
import datetime
from dotenv import load_dotenv
import openai
from openai import OpenAIError
from utils import api_call_with_refresh
import streamlit.components.v1 as components



load_dotenv()

# Retrieve the environment variable in Python
django_url = os.getenv("DJANGO_URL")

# Use concatenation to insert the variable into the JavaScript
components.html("""
<script>
let ws = new WebSocket("ws://127.0.0.1:8000/ws/toolcall/");

ws.onmessage = function(event) {
    let receivedData = JSON.parse(event.data);
    // Use Streamlit's JavaScript API to set a hidden Streamlit input
    Streamlit.setComponentValue(receivedData);
};
</script>
""", height=0)  # Height set to 0 to hide the component
    
openai_env_key = os.getenv("OPENAI_KEY")

if openai_env_key:
    openai.api_key = openai_env_key

client = openai

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
        st.markdown(f"**Latest Weight:** {latest_metrics['weight']} kg")
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
        df = pd.DataFrame(metric_trends)
        
        df['date'] = pd.to_datetime(df['date_recorded'])
        
        df.set_index('date', inplace=True)
        
        min_date, max_date = df.index.min(), df.index.max()

        # If only one data point is available, it cannot plot a range
        if min_date == max_date:
            st.warning("Only one data point available. Displaying the data without range selection.")
            st.line_chart(df[['weight', 'bmi', 'energy_level']])
        else:
            selected_range = st.select_slider(
                "Select Date Range", 
                options=pd.date_range(min_date, max_date, freq='D'),
                value=(min_date, max_date)
            )

            filtered_df = df.loc[selected_range[0]:selected_range[1]]

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
        st.error("No health metrics data available to display.")

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
    with st.sidebar.expander("Health Metrics", expanded=False):  # Set expanded to False
        with st.form(key='health_metrics_form'):
            date = st.date_input("Date", value=datetime.date.today())
            weight = st.number_input("Weight (kg)", min_value=0.0, format="%.2f")
            bmi = st.number_input("BMI", min_value=0.0, format="%.2f")
            mood = st.selectbox("Mood", ["Happy", "Sad", "Stressed", "Relaxed", "Energetic", "Tired", "Neutral"])
            energy_level = st.slider("Energy Level", 1, 10, 5)

            submit_button = st.form_submit_button(label='Submit')
            if submit_button:
                # If no input is made, the value will be None
                weight = weight if weight != 0.0 else None
                bmi = bmi if bmi != 0.0 else None
                save_health_metrics(date, weight, bmi, mood, energy_level)


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

    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

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
    chat_container = st.container()

    # Display chat history using st.chat_message
    for message in st.session_state.chat_history:
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])

    # Replace text_input with st.chat_input
    prompt = st.chat_input("Enter your question:")

    if prompt:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
        thread_id = st.session_state.thread_id 
        ws_data = st.empty()  # Placeholder for displaying WebSocket data
        # Check for new data periodically
        if 'new_ws_data' in st.session_state:
            # Process and display the WebSocket data
            ws_data.json(st.session_state['new_ws_data'])

        # Process the question and get response
        # full_response = handle_openai_communication(prompt, thread_id, {"user_id": st.session_state.get('user_id')})
        # Interaction with the chat_with_gpt endpoint

        full_response = chat_with_gpt(prompt, thread_id, user_id=st.session_state.get('user_id'))
        print('full_response:', full_response)
        if full_response:
            st.session_state.thread_id = full_response['new_thread_id']
            st.session_state.chat_history.append({"role": "assistant", "content": full_response['last_assistant_message']})
            # Dynamically update the chat container
            with chat_container.chat_message("assistant"):
                st.markdown(full_response['last_assistant_message'])


        else:
            st.error("Could not get a response, please try again.")


    if st.button("Start New Chat"):
        st.session_state.thread_id = None
        st.session_state.chat_history = []
        chat_container.empty()
        st.rerun()
        st.success("New chat started. Please enter your question.")


if __name__ == "__main__":
    assistant()
