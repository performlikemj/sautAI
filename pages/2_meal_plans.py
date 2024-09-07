import streamlit as st
import pandas as pd
from utils import (api_call_with_refresh, login_form, toggle_chef_mode, 
                   start_or_continue_streaming, client, openai_headers, guest_chat_with_gpt, chat_with_gpt, is_user_authenticated, resend_activation_link)
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import math
import json

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

def meal_plans():

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
    try:    
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
            login_form()

        # Check if the user is logged in and their email is confirmed
        if is_user_authenticated() and st.session_state.get('email_confirmed', False):
            if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
                st.title("Your Meal Plans")
            
            if 'selected_week_start' not in st.session_state:
                st.session_state.selected_week_start = datetime.now().date() - timedelta(days=datetime.now().date().weekday())

            # Ensure selected_day is initialized
            if 'selected_day' not in st.session_state:
                st.session_state.selected_day = "All Days"



            selected_week_start = st.session_state.selected_week_start
            selected_week_end = selected_week_start + timedelta(days=6)

            # Week navigation
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button('Previous Week'):
                    st.session_state.selected_week_start -= timedelta(weeks=1)
                    st.session_state.selected_day = "All Days"  # Reset to "All Days" when navigating weeks
                    st.rerun()
            with col3:
                if st.button('Next Week'):
                    st.session_state.selected_week_start += timedelta(weeks=1)
                    st.session_state.selected_day = "All Days"  # Reset to "All Days" when navigating weeks
                    st.rerun()

            st.subheader(f"Meal Plans for Week: {selected_week_start} - {selected_week_end}")

            # Day selection within the current week
            days_of_week = [(selected_week_start + timedelta(days=i)).strftime('%A') for i in range(7)]
            all_days_options = ["All Days"] + days_of_week

            # Determine the index of the selected day
            selected_day_index = all_days_options.index(st.session_state.selected_day)

            selected_day = st.selectbox(
                "Select a Day",
                options=all_days_options,
                index=selected_day_index
            )
            # Update the selected day in the session state
            st.session_state.selected_day = selected_day

            # Check if the selected week is in the past
            is_past_week = selected_week_end < datetime.now().date()

            # API call to fetch meal plans
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/meals/api/meal_plans/?week_start_date={selected_week_start}',
                method='get',
                headers=headers,
            )

            if response.status_code == 200:
                meal_plan_data = response.json()
                meal_plan_records = []

                for meal_plan in meal_plan_data:
                    meal_plan_id = meal_plan['id']  # Extract meal_plan_id
                    if not meal_plan['meals']:
                        continue
                    
                    day_offset = {
                        'Monday': 0,
                        'Tuesday': 1,
                        'Wednesday': 2,
                        'Thursday': 3,
                        'Friday': 4,
                        'Saturday': 5,
                        'Sunday': 6,
                    }

                    for meal in meal_plan['meals']:
                        meal_day = meal['day']
                        meal_plan_meal_id = meal['meal_plan_meal_id']  # Now you have access to the MealPlanMeal ID
                        meal_date = selected_week_start + timedelta(days=day_offset[meal_day])
                        meal_plan_records.append({
                            'Select': False,  # Add a checkbox for selection
                            'Meal Plan ID': meal_plan_id,  
                            'Meal Plan Meal ID': meal_plan_meal_id,  # Use this ID for further actions
                            'meal_id': meal['meal']['id'],
                            'Meal Date': meal_date.strftime('%Y-%m-%d'),
                            'Meal Name': meal['meal']['name'],
                            'Day': meal_day,
                            'Meal Type': meal['meal_type'],
                            'Description': meal['meal']['description'],
                        })

                if not meal_plan_records:
                    st.info("No meals found for this week.")
                    return

                meal_plan_df = pd.DataFrame(meal_plan_records)

                # Apply day filter if a specific day is selected
                if selected_day != "All Days":
                    meal_plan_df = meal_plan_df[meal_plan_df['Day'] == selected_day]

                # Order the days from Monday to Sunday and then by Meal Type
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                meal_type_order = ['Breakfast', 'Lunch', 'Dinner']
                meal_plan_df['Day'] = pd.Categorical(meal_plan_df['Day'], categories=day_order, ordered=True)
                meal_plan_df['Meal Type'] = pd.Categorical(meal_plan_df['Meal Type'], categories=meal_type_order, ordered=True)
                meal_plan_df = meal_plan_df.sort_values(['Day', 'Meal Type'])
                # Display the meal plan in an editable table with row selection
                # Display the meal plan in an editable table with row selection
                selected_rows = st.data_editor(
                    meal_plan_df,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    column_config={"Select": st.column_config.CheckboxColumn(required=True)},
                )

                # Action Buttons
                st.markdown("---")
                st.write("### Actions for Selected Meals")
                if st.button('Change Selected Meals', disabled=is_past_week):
                    selected_meals = selected_rows[selected_rows['Select']]
                    # Drop the 'Select' column from the result
                    selected_data = selected_meals.drop('Select', axis=1)  # Removes the 'Select' column from the selected rows
                    # Extracting relevant information
                    meal_plan_id = selected_data['Meal Plan ID'].iloc[0]  # Get the first meal_plan_id from selected rows
                    old_meal_ids = selected_data['meal_id'].tolist()                    
                    days_of_meal = selected_data['Day'].tolist()
                    meal_types = selected_data['Meal Type'].tolist()
                    preferred_language = st.session_state.user_info.get('preferred_language', 'English')
                    # Formatting the user details prompt
                    user_details_prompt = (
                        f"Consider the following user details when changing the user's meals:\n"
                        f"- Answering in the user's preferred language: {preferred_language}\n"
                        f"- The meal plan id: {meal_plan_id}\n"
                        f"- The current/old meal id(s): {', '.join(map(str, old_meal_ids))}\n"  # Convert meal IDs to string and join
                        f"- The day(s) of the meal: {', '.join(days_of_meal)}\n"
                        f"- The meal type(s) (breakfast, lunch, dinner): {', '.join(meal_types)}\n"
                    )
                    prompt = "Please change the selected meal(s)"
                    user_id = st.session_state.get('user_id')
                    try:
                        response = chat_with_gpt(user_details_prompt, st.session_state.thread_id, user_id=user_id) if is_user_authenticated() else guest_chat_with_gpt(user_details_prompt, st.session_state.thread_id)
                    except Exception as e:
                        st.error("Failed to communicate with the assistant. Please try again.")
                        logging.error(f"Assistant communication error: {e}")
                        return                    
                    if response and 'new_thread_id' in response:
                        logging.info(f"New thread ID: {response['new_thread_id']}")
                        st.session_state.thread_id = response['new_thread_id']
                    start_or_continue_streaming(client, user_id=st.session_state.user_info['user_id'], openai_headers=openai_headers, chat_container=None, user_details_prompt=user_details_prompt, prompt=prompt, change_meals=True) 
                    st.rerun()



                if st.button('Generate Cooking Instructions'):
                    selected_meals = selected_rows[selected_rows['Select']]
                    selected_data = selected_meals.drop('Select', axis=1)

                    # Extract meal_plan_meal_ids
                    meal_plan_meal_ids = selected_data['Meal Plan Meal ID'].tolist()

                    # Ensure that meal_plan_meal_ids is not empty before making the API call
                    if not meal_plan_meal_ids:
                        st.error("No meals selected. Please select meals before generating instructions.")
                        return

                    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    payload = {'meal_plan_meal_ids': meal_plan_meal_ids}

                    try:
                        # First, initiate the cooking instruction generation
                        with st.spinner("Generating cooking instructions..."):
                            generation_response = api_call_with_refresh(
                                url=f'{os.getenv("DJANGO_URL")}/meals/api/generate_cooking_instructions/',
                                method='post',
                                headers=headers,
                                data=payload
                            )

                        # Check if response is valid
                        if generation_response.status_code == 200:
                            st.success("Cooking instructions generation initiated successfully.")

                            # Fetch the generated instructions
                            with st.spinner("Fetching cooking instructions..."):
                                fetch_response = api_call_with_refresh(
                                    url=f'{os.getenv("DJANGO_URL")}/meals/api/fetch_instructions/?meal_plan_meal_ids=' + ','.join(map(str, meal_plan_meal_ids)),
                                    method='get',
                                    headers=headers,
                                )

                            if fetch_response.status_code == 200:
                                st.session_state['instructions'] = fetch_response.json().get('instructions', [])

                                if not st.session_state['instructions']:
                                    st.info("No instructions available yet. Please check back later.")
                                else:
                                    display_instructions_pagination()
                            else:
                                st.error(f"Error fetching instructions: {fetch_response.json().get('error', 'Unknown error occurred.')}")
                        else:
                            st.error(f"Error generating instructions: {generation_response.json().get('error', 'Unknown error occurred.')}")
                    except Exception as e:
                        logging.error(f"Failed to generate or fetch cooking instructions: {e}")
                        st.error("Failed to generate or fetch cooking instructions. Please try again.")


                # Approve Meal Plan Button
                if st.button('Approve Meal Plan', disabled=is_past_week):
                    if not meal_plan_df.empty:  # Ensure the meal_plan_df is not empty
                        meal_plan_id = int(meal_plan_df['Meal Plan ID'].iloc[0])  # Get the meal_plan_id from the first row
                        user_id = int(st.session_state.user_info['user_id'])  # Get the user ID from session state

                        # Prepare payload for the API call
                        payload = {
                            'user_id': user_id,
                            'meal_plan_id': meal_plan_id
                        }

                        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

                        # Call the backend API to approve the meal plan
                        try:
                            with st.spinner("Approving meal plan..."):
                                response = api_call_with_refresh(
                                    url=f'{os.getenv("DJANGO_URL")}/meals/api/approve_meal_plan/',
                                    method='post',
                                    headers=headers,
                                    data=payload,
                                )
                        except Exception as e:
                            logging.error(f"Failed to approve meal plan: {e}")
                            st.error("Failed to approve meal plan. Please try again.")
                            return

                        # Process the response
                        if response.status_code == 200:
                            result = response.json()
                            if result['status'] == 'success':
                                st.success(result['message'])
                                if 'order_id' in result:
                                    st.info(f"Order ID: {result['order_id']} - Proceed to payment.")
                            else:
                                st.info(result['message'])
                        else:
                            st.error(f"Error: {response.json().get('message', 'Unknown error occurred.')}")
                    else:
                        st.error("No meal plans found for approval.")


            else:
                logging.error(f"Failed to fetch meal plans. Status code: {response.status_code}, Response: {response.text}")
                st.error("Error fetching meal plans.")

        # If the email is not confirmed, restrict access and prompt to resend activation link
        elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
            st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
            if st.button("Resend Activation Link"):
                resend_activation_link(st.session_state['user_id'])

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

# Fragment to handle instructions display and pagination
@st.fragment
def display_instructions_pagination():
    instructions = st.session_state.get('instructions', [])
    
    if not instructions:
        st.error("No instructions available.")
        return
    
    # Total number of meals for pagination
    num_meals = len(instructions)

    # Add a pagination control for meals
    current_meal_idx = st.selectbox(f"Select Meal", range(num_meals), format_func=lambda i: f"Meal Plan Meal ID {instructions[i]['meal_plan_meal_id']}")

    # Display only the selected meal's instructions
    selected_meal_instructions = instructions[current_meal_idx]
    meal_plan_meal_id = selected_meal_instructions.get('meal_plan_meal_id')
    instructions_json_str = selected_meal_instructions.get('instructions')

    if instructions_json_str:
        try:
            # Deserialize the JSON string into a dictionary
            instructions_data = json.loads(instructions_json_str)
            steps = instructions_data.get('steps')

            if steps:
                # Display the selected meal's instructions
                st.subheader(f"Instructions for Meal Plan Meal ID {meal_plan_meal_id}")
                for step in steps:
                    step_number = step.get('step_number', 'Unknown')
                    description = step.get('description', 'No description available')
                    duration = step.get('duration', 'No duration')

                    # Display each step with markdown
                    st.markdown(f"**Step {step_number}:** {description}")
                    st.markdown(f"**Duration:** {duration}")

        except json.JSONDecodeError as e:
            st.error(f"Failed to parse instructions for MealPlanMeal ID {meal_plan_meal_id}.")
            logging.error(f"JSONDecodeError: {str(e)}")
    else:
        st.warning(f"Instructions not yet available for Meal Plan Meal ID {meal_plan_meal_id}.")

if __name__ == "__main__":
    meal_plans()
