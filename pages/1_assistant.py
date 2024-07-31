import os
import time
import pytz
from typing_extensions import override
import requests
import json
import streamlit as st
import pandas as pd
import datetime as dt
from dotenv import load_dotenv
import openai
from openai import OpenAIError
from openai import AssistantEventHandler, OpenAI
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import ToolCall, RunStep
from openai.types.beta import AssistantStreamEvent
from openai.types.beta.threads import Text, TextDelta
from utils import api_call_with_refresh, is_user_authenticated, login_form, toggle_chef_mode
import numpy as np
import logging

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

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="auto",
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



@st.experimental_dialog("Understanding Portion Sizes")
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

@st.experimental_fragment
def calorie_intake_form(selected_date=None):
    # Fetch the user's time zone from session state
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    # Get the current date and time in the user's time zone
    local_date = dt.datetime.now(local_tz).date()

    # Use selected_date if provided, else default to local_date
    if selected_date is not None:
        selected_date = selected_date
    else:
        selected_date = local_date

    with st.sidebar:
        with st.expander("Calorie Intake", expanded=False):
            with st.form(key='calorie_intake_form'):
                # Convert selected_date to the user's time zone
                selected_date_input = st.date_input("Date", value=selected_date, key='calorie_date')
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
                portion_size = st.selectbox("Portion Size", options=list(portion_size_options.keys()), format_func=lambda x: portion_size_options[x], key='portion_size')

                submit_button = st.form_submit_button(label='Submit')
                if submit_button:
                    user_id = st.session_state.get('user_id')
                    meal_name = st.session_state['meal_name']
                    meal_description = st.session_state['meal_description']
                    selected_date = st.session_state['calorie_date']
                    selected_date = local_tz.localize(dt.combine(selected_date_input, dt.min.time()))  # Localize to user's timezone
                    add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date)

            open_modal_button = st.button("Understand Portion Sizes?", key="open-portion-size-info")
            if open_modal_button:
                show_portion_size_dialog()


@st.experimental_fragment
def visualize_calorie_data():
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    user_id = st.session_state.get('user_id')
    selected_date = st.date_input("Select Date for Calorie Data", value=dt.datetime.now(local_tz).date())

    st.write("### Select Date for Calorie Data")
    selected_date = st.date_input("Date", value=selected_date)
    
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
    response = requests.delete(
        f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/delete_calorie_intake/{record_id}/',
        headers=headers
    )
    if response.status_code == 200:
        st.success("Calorie record deleted successfully")
        st.rerun() 
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

    if not filtered_df.empty and not filtered_df[metric_name].isna().all():
        st.subheader(f"{metric_name.capitalize()} Trend")
        st.line_chart(filtered_df[metric_name])
    else:
        st.warning(f"No data available for {metric_name} in the selected date range. Please check if the data exists for this range.")

def plot_metric_trends(metric_trends):
    if metric_trends and isinstance(metric_trends, list) and isinstance(metric_trends[0], dict):
        df = pd.DataFrame(metric_trends)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
        df['bmi'] = pd.to_numeric(df['bmi'], errors='coerce')
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
            plot_metric_trend('bmi', df, selected_range)
            plot_metric_trend('energy_level', df, selected_range)
    else:
        st.warning("No metric trends available to display.")

@st.experimental_fragment
def health_metrics_form():
    # Add a session state variable for weight unit if not present
    if 'weight_unit' not in st.session_state:
        st.session_state['weight_unit'] = 'kg'  # default unit
        
    # Fetch the user's time zone from session state
    user_timezone = st.session_state.get('timezone', 'UTC')
    local_tz = pytz.timezone(user_timezone)

    with st.sidebar.expander("Health Metrics", expanded=False):  # Set expanded to False
        weight_unit = st.radio("Weight Unit", ('kg', 'lbs'))
        st.session_state['weight_unit'] = weight_unit

        with st.form(key='health_metrics_form'):
            # Convert current date to user's time zone
            local_date = dt.datetime.now(local_tz).date()
            date_input = st.date_input("Date", value=local_date)
            weight_input = st.number_input(f"Weight ({st.session_state['weight_unit']})", min_value=0.0, format="%.2f")
            weight = weight_input if st.session_state['weight_unit'] == 'kg' else np.round(weight_input / 2.20462, 2)
            bmi = st.number_input("BMI", min_value=0.0, format="%.2f")
            mood = st.selectbox("Mood", ["Happy", "Sad", "Stressed", "Relaxed", "Energetic", "Tired", "Neutral"])
            energy_level = st.slider("Energy Level", 1, 10, 5)

            submit_button = st.form_submit_button(label='Submit')
            if submit_button:
                weight = weight if weight != 0.0 else None
                bmi = bmi if bmi != 0.0 else None
                date_to_save = local_tz.localize(dt.datetime.combine(date_input, dt.datetime.min.time()))  # Localize to user's timezone
                save_health_metrics(date_to_save, weight, bmi, mood, energy_level)


def guest_chat_with_gpt(prompt, thread_id):
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

def chat_with_gpt(prompt, thread_id, user_id):
    response_data = requests.post(
        f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/chat_with_gpt/', 
        data={'question': prompt, 'thread_id': thread_id, 'user_id': user_id}
    )
    if response_data.status_code == 200:
        return response_data.json()
    else:
        st.error("Sorry. There was an error communicating with your assistant. Please try again.")
        return None

class EventHandler(AssistantEventHandler):
    def __init__(self, thread_id, chat_container, user_id=None):
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
        # response_text = text.value  # Ensure this line correctly extracts the text value.
        # print(f"Streaming response text: {response_text}")  # Debug print
        # with self.chat_container.chat_message("assistant"):
        #     st.write_stream(self.response_generator(response_text))
        # st.session_state.chat_history.append({"role": "assistant", "content": response_text})


    @override
    def on_text_delta(self, delta, snapshot):
        pass

    def on_text_done(self, text) -> None:
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

@st.experimental_fragment
def assistant():
    try:
        # Login Form
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
            login_form()

        # Logout Button
        if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
            if st.button("Logout", key='form_logout'):
                # Clear session state as well
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()
            # Call the toggle_chef_mode function
            toggle_chef_mode()

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

        # Additional functionalities for authenticated users not in chef mode
        if 'is_logged_in' in st.session_state and st.session_state['is_logged_in'] and st.session_state.get('current_role', '') != 'chef':
            st.title("Dietician Assistant")

            if is_user_authenticated():
                # Calorie Intake Form in the Sidebar
                calorie_intake_form(dt.date.today())

                # Calorie Data Visualization
                with st.expander("View Calorie Data", expanded=False):
                    visualize_calorie_data()

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

            

            if not st.session_state.get('showed_user_summary', False):
                headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                user_summary_response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_summary/',
                    method='get',
                    headers=headers,
                    data={"user_id": st.session_state.get('user_id')}
                )
                if user_summary_response.status_code == 200:
                    # Extract the summary text from the response
                    data = user_summary_response.json()  # Parse the JSON response
                    user_summary = data['data'][0]['content'][0]['text']['value']
                    recommend_prompt = data.get('recommend_prompt', '')

                    # Append the summary to the chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": user_summary})
                    st.session_state.recommend_prompt = recommend_prompt
                    # Set the flag to True so it doesn't show again in the same session
                    st.session_state['showed_user_summary'] = True

        # Check if a thread was selected in history
        if 'selected_thread_id' in st.session_state:
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
                chat_history.sort(key=lambda x: x['created_at'])

                for msg in chat_history:
                    st.session_state.chat_history.append({"role": msg['role'], "content": msg['content']})
            else:
                st.error("Error fetching thread details.")

        chat_container = st.container()
        
        # Use a container to dynamically update chat messages
        st.info("Response time may vary. Your patience is appreciated.")


        def process_user_input(prompt, chat_container):
            user_id = st.session_state.get('user_id')
            # Update chat history immediately with the follow-up prompt
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            # Send the prompt to the backend and get a message ID
            if is_user_authenticated():
                # Determine the location detail to use (country or timezone)
                location = st.session_state.get('country', st.session_state.get('timezone', 'UTC'))
                # Prepare the prompt with user details
                user_details_prompt = (
                    f"Consider the following user details while responding:\n"
                    f"- Dietary Preference: {st.session_state.get('dietary_preference', 'Everything')}\n"
                    f"- Custom Dietary Preference: {st.session_state.get('custom_dietary_preference', 'None')}\n"
                    f"- Allergies: {', '.join(st.session_state.get('allergies', [])) if st.session_state.get('allergies') else 'None'}\n"
                    f"- Custom Allergies: {', '.join(st.session_state.get('custom_allergies', [])) if st.session_state.get('custom_allergies') else 'None'}\n"
                    f"- Location: {location}\n"
                    f"- Preferred Language: {st.session_state.get('preferred_language', 'English')}\n"
                    f"- Goal: {st.session_state.get('goal_name', 'No specific goal')}: {st.session_state.get('goal_description', 'No description provided')}\n"
                    f"Question: {prompt}\n"
                )
                print(f'User details prompt: {user_details_prompt}')
            response = chat_with_gpt(user_details_prompt, st.session_state.thread_id, user_id=user_id) if is_user_authenticated() else guest_chat_with_gpt(prompt, st.session_state.thread_id)
            openai_headers = {
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            }
            if response and 'new_thread_id' in response:
                logging.info(f"New thread ID: {response['new_thread_id']}")
                st.session_state.thread_id = response['new_thread_id']
                try:
                    # Start or continue streaming responses
                    with client.beta.threads.runs.stream(
                        thread_id=st.session_state.thread_id,
                        assistant_id=os.getenv("ASSISTANT_ID") if is_user_authenticated() else os.getenv("GUEST_ASSISTANT_ID"),
                        event_handler=EventHandler(st.session_state.thread_id, chat_container, user_id),
                        instructions=user_details_prompt if is_user_authenticated() else prompt,  # Or set general instructions for your assistant
                        extra_headers=openai_headers
                    ) as stream:
                        stream.until_done()
                except openai.BadRequestError as e:
                    if 'already has an active run' in str(e):
                        st.session_state.thread_id = None
                        logging.error(e)
                        st.error("The current thread already has an active run. Please start a new chat.")
            elif response and 'last_assistant_message' in response:
                st.session_state.thread_id = response['new_thread_id']

                st.session_state.recommend_follow_up = response['recommend_follow_up']
                st.session_state.chat_history.append({"role": "assistant", "content": response['last_assistant_message']})
                with chat_container.chat_message("assistant"):
                    st.markdown(response['last_assistant_message'])
            else:
                st.error("Could not get a response, please try again.")

        # Chat functionality available to unauthenticated users or authenticated non-chef users
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in'] or (st.session_state.get('current_role', '') != 'chef'):
            # Process and display chat interactions
            for message in st.session_state.chat_history:
                with chat_container.chat_message(message["role"]):
                    st.markdown(message["content"])

            if st.session_state.recommend_follow_up:
                with st.container():
                    st.write("Recommended Follow-Ups:")
                    for follow_up in st.session_state.recommend_follow_up:
                        st.button(follow_up, key=follow_up, on_click=lambda follow_up=follow_up: process_user_input(follow_up, chat_container))

            if st.session_state.recommend_prompt:
                with st.container():
                    st.write("Recommended Follow-Ups:")
                    for follow_up_prompt in st.session_state.recommend_prompt:
                        st.button(follow_up_prompt, key=follow_up_prompt, on_click=lambda follow_up_prompt=follow_up_prompt: process_user_input(follow_up_prompt, chat_container))
                    st.session_state.recommend_prompt = ""

            prompt = st.chat_input("Enter your question:")
            if prompt:
                process_user_input(prompt, chat_container)

            # Button to start a new chat
            if st.session_state.chat_history and st.button("Start New Chat"):
                st.session_state.thread_id = None
                st.session_state.chat_history = []
                st.session_state.selected_thread_id = None
                st.session_state.recommend_follow_up = []
                chat_container.empty()
                st.rerun()
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")


if __name__ == "__main__":
    assistant()
