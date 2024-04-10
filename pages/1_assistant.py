import os
import time
from typing_extensions import override
import requests
import json
import streamlit as st
import pandas as pd
import datetime
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
import streamlit.components.v1 as components
import numpy as np
from streamlit_modal import Modal

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
                    st.experimental_rerun()  # Refresh data
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


# Define the portion size explanation modal
portion_size_modal = Modal(
    "Understanding Portion Sizes", 
    key="portion-size-modal",
    padding=20,
    max_width=744
)

def calorie_intake_form(selected_date):
    with st.sidebar:
        with st.expander("Calorie Intake", expanded=True):
            # Portion size explanation setup
            portion_size_modal = Modal(
                "Understanding Portion Sizes",
                key="portion-size-modal",
                padding=20,
                max_width=744
            )
            

            with st.form(key='calorie_intake_form'):
                st.date_input("Date", value=selected_date, key='calorie_date')
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
                    # Retrieving the values
                    meal_name = st.session_state['meal_name']
                    meal_description = st.session_state['meal_description']
                    selected_date = st.session_state['calorie_date']
                    add_calorie_intake(user_id, meal_name, meal_description, portion_size, selected_date)

            # Trigger for the portion size explanation modal
            # Placed outside the form but within the same expander for UI consistency
            open_modal_button = st.button("Understand Portion Sizes?", key="open-portion-size-info")
            if open_modal_button:
                portion_size_modal.open()


if portion_size_modal.is_open():
    with portion_size_modal.container():
        with st.container():
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
    # Check if metric_trends is not empty and the first item is a dictionary
    if metric_trends and isinstance(metric_trends, list) and isinstance(metric_trends[0], dict):
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
        st.warning("No metric trends available to display.")


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
        print(f"\nassistant on_text_created > ", end="", flush=True)
        # response_text = text.value  # Ensure this line correctly extracts the text value.
        # print(f"Streaming response text: {response_text}")  # Debug print
        # with self.chat_container.chat_message("assistant"):
        #     st.write_stream(self.response_generator(response_text))
        # st.session_state.chat_history.append({"role": "assistant", "content": response_text})


    @override
    def on_text_delta(self, delta, snapshot):
        print(f"{delta.value}")

    def on_text_done(self, text) -> None:
        print('text:', text)
        response_text = text.value
        with self.chat_container.chat_message("assistant"):
            st.write_stream(self.response_generator(response_text))
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    def on_end(self):
        print("on_end")
        tool_outputs = []
        if self.current_run_step_snapshot and self.current_run_step_snapshot.step_details.type == 'tool_calls':
            print(f"\nTool Calls: {self.current_run_step_snapshot.step_details.tool_calls}")
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
                print(f"\nTool Call Result: {tool_call_result.json()}")
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
                event_handler=EventHandler(self.thread_id, chat_container=self.chat_container, user_id=self.user_id)
            ) as stream:
                stream.until_done()


    @override
    def on_exception(self, exception: Exception) -> None:
        print(f"\nassistant > {exception}\n", end="", flush=True)

    @override
    def on_message_created(self, message: Message) -> None:
        print(f"\nassistant on_message_created > {message}\n", end="", flush=True)

    @override
    def on_message_done(self, message: Message) -> None:
        print(f"\nassistant on_message_done > {message}\n", end="", flush=True)


    @override
    def on_message_delta(self, delta: MessageDelta, snapshot: Message) -> None:
        pass


    @override
    def on_tool_call_done(self, tool_call: ToolCall) -> None:       
        keep_retrieving_run = client.beta.threads.runs.retrieve(
            thread_id=self.thread_id,
            run_id=self.run_id
        )

        print(f"\nDONE STATUS: {keep_retrieving_run.status}")

        if keep_retrieving_run.status == "completed":
            all_messages = client.beta.threads.messages.list(
                thread_id=self.thread_id
            )

            print(all_messages.data[0].content[0].text.value, "", "")
            return

        elif keep_retrieving_run.status == "requires_action":
            print("here you would call your function")
            print(f'self.tool_calls: {self.tool_calls}')

        else:
            print(f"\nassistant on_tool_call_done > {tool_call}\n", end="", flush=True)

    @override
    def on_run_step_created(self, run_step: RunStep) -> None:
        print(f"on_run_step_created")
        self.run_id = run_step.run_id
        self.run_step = run_step
        print("The type of run_step run step is ", type(run_step), flush=True)
        print(f"\n run step created assistant > {run_step}\n", flush=True)

    @override
    def on_run_step_done(self, run_step: RunStep) -> None:
        print(f"\n run step done assistant > {run_step}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot): 
        if delta.type == 'function':
            print(delta.function.arguments, end="", flush=True)
            self.arguments += delta.function.arguments
        elif delta.type == 'code_interpreter':
            print(f"on_tool_call_delta > code_interpreter")
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
        else:
            print("ELSE")
            print(delta, end="", flush=True)

    @override
    def on_event(self, event: AssistantStreamEvent) -> None:
        if event.event == "thread.run.requires_action":
            print("\nthread.run.requires_action > submit tool call")
            print(f"ARGS: {self.arguments}")


def assistant():
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



    # Additional functionalities for authenticated users not in chef mode
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in'] and st.session_state.get('current_role', '') != 'chef':
        st.title("Dietician Assistant")

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

        chat_container = st.container(height=400)


        if not st.session_state.get('showed_user_summary', False):
            print('st.session_state.get(user_id):', st.session_state.get('user_id'))
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
                
                # Append the summary to the chat history
                st.session_state.chat_history.append({"role": "assistant", "content": user_summary})
                
                
                # Set the flag to True so it doesn't show again in the same session
                st.session_state['showed_user_summary'] = True

    # Use a container to dynamically update chat messages
    st.info("Response time may vary. Your patience is appreciated.")

    def process_user_input(prompt):
        user_id = st.session_state.get('user_id')
        # Update chat history immediately with the follow-up prompt
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
        # Send the prompt to the backend and get a message ID
        response = chat_with_gpt(prompt, st.session_state.thread_id, user_id=user_id) if is_user_authenticated() else guest_chat_with_gpt(prompt, st.session_state.thread_id)
        print('response:', response)

        if response and 'new_thread_id' in response:
            st.session_state.thread_id = response['new_thread_id']
            # Start or continue streaming responses
            print(f'from elif response thread_id:', st.session_state.thread_id)
            with client.beta.threads.runs.create_and_stream(
                thread_id=st.session_state.thread_id,
                assistant_id=os.getenv("ASSISTANT_ID") if is_user_authenticated() else os.getenv("GUEST_ASSISTANT_ID"),
                event_handler=EventHandler(st.session_state.thread_id, chat_container, user_id),
                instructions=prompt,  # Or set general instructions for your assistant
            ) as stream:
                stream.until_done()
        elif response and 'last_assistant_message' in response:
            st.session_state.thread_id = response['new_thread_id']

            st.session_state.recommend_follow_up = response['recommend_follow_up']
            print('from elif response:', response['last_assistant_message'])
            st.session_state.chat_history.append({"role": "assistant", "content": response['last_assistant_message']})
            print('from elif st.session_state.chat_history:', st.session_state.chat_history)
            with chat_container.chat_message("assistant"):
                st.markdown(response['last_assistant_message'])
                print('from elif st.session_state.chat_history:', st.session_state.chat_history)
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
                    st.button(follow_up, key=follow_up, on_click=lambda follow_up=follow_up: process_user_input(follow_up))

        prompt = st.chat_input("Enter your question:")
        if prompt:
            process_user_input(prompt)

        # Button to start a new chat
        if st.session_state.chat_history and st.button("Start New Chat"):
            st.session_state.thread_id = None
            st.session_state.chat_history = []
            st.session_state.recommend_follow_up = []
            chat_container.empty()
            st.rerun()


if __name__ == "__main__":
    assistant()
