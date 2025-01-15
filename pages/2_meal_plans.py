import streamlit as st
import pandas as pd
from utils import (
    api_call_with_refresh, login_form, toggle_chef_mode, 
    start_or_continue_streaming, client, openai_headers, guest_chat_with_gpt, 
    chat_with_gpt, is_user_authenticated, resend_activation_link, footer
)
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import json
import requests
import traceback

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

def meal_plans():
    # Parse query parameters for email link scenario
    meal_plan_id_from_url = st.query_params.get('meal_plan_id')
    meal_id_from_url = st.query_params.get('meal_id')
    action = st.query_params.get('action', None)

    # Check for approval token (email approval flow)
    approval_token = st.query_params.get('approval_token')
    meal_prep_preference = st.query_params.get('meal_prep_preference')

    if approval_token and action == "approve_meal_plan":
        try:
            response = requests.post(
                f'{os.getenv("DJANGO_URL")}/meals/api/email_approved_meal_plan/',
                data={'approval_token': approval_token, 'meal_prep_preference': meal_prep_preference}
            )
            if response.status_code == 200:
                st.success('Your meal plan has been approved!')
            else:
                st.error('Invalid or expired approval token.')
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"traceback: {traceback.format_exc()}")
        return

    elif approval_token and action == "generate_emergency_plan":
        st.info("Generating your emergency pantry plan...")
        try:
            # Now we don't need user_id in the URL since the server uses request.user
            url = f"{os.getenv('DJANGO_URL')}/meals/api/generate_emergency_supply/"
            user_id = st.query_params.get('user_id')
            payload = {'user_id':user_id, 'approval_token':approval_token}
            resp = requests.post(
                url=url,
                data=payload  
            )
            
            if resp.status_code == 200:
                st.success("Emergency supply list generated successfully! Check your email for details.")
            else:
                st.error(f"Error generating emergency plan. {resp.text}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
        return

    # Handle auth and logout
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='form_logout'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
        toggle_chef_mode()
    else:
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
            login_form()

    # Check if user is authenticated and email confirmed
    if is_user_authenticated() and st.session_state.get('email_confirmed', False):
        if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
            st.title("Your Meal Plans")
            st.markdown("""
            Welcome to your personalized meal planning dashboard! Here, you can view, edit, and optimize your weekly meal plans to suit your dietary preferences and lifestyle.

            If you encounter any issues or need assistance, feel free to contact support@sautai.com.
            """)




        if 'selected_week_start' not in st.session_state:
            st.session_state.selected_week_start = datetime.now().date() - timedelta(days=datetime.now().date().weekday())
        if 'selected_day' not in st.session_state:
            st.session_state.selected_day = "All Days"

        selected_week_start = st.session_state.selected_week_start
        selected_week_end = selected_week_start + timedelta(days=6)
        is_past_week = selected_week_end < datetime.now().date()

        # Week navigation
        col1, _, col3 = st.columns([1,1,1])
        with col1:
            if st.button('Previous Week'):
                st.session_state.selected_week_start -= timedelta(weeks=1)
                st.session_state.selected_day = "All Days"
                st.rerun()
        with col3:
            if st.button('Next Week'):
                st.session_state.selected_week_start += timedelta(weeks=1)
                st.session_state.selected_day = "All Days"
                st.rerun()

        st.subheader(f"Meal Plans for Week: {selected_week_start} - {selected_week_end}")

        days_of_week = [(selected_week_start + timedelta(days=i)).strftime('%A') for i in range(7)]
        all_days_options = ["All Days"] + days_of_week
        selected_day = st.selectbox(
            "Select a Day",
            options=all_days_options,
            index=all_days_options.index(st.session_state.selected_day)
        )
        st.session_state.selected_day = selected_day

        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/meal_plans/?week_start_date={selected_week_start}',
            method='get',
            headers=headers,
        )

        if response.status_code == 200:
            meal_plan_data = response.json()
            if not meal_plan_data:
                st.info("No meals found for this week.")
                return

            # Assume one meal plan for simplicity
            meal_plan = meal_plan_data[0]
            meal_plan_id = meal_plan['id']
            st.session_state['meal_prep_preference'] = meal_plan['meal_prep_preference']

            meal_plan_details_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/meal_plans/{meal_plan_id}/",
                method='get',
                headers=headers
            )

            is_approved = False
            if meal_plan_details_resp.status_code == 200:
                meal_plan_details = meal_plan_details_resp.json()
                is_approved = meal_plan_details.get('is_approved', False)

            meal_plan_records = []
            day_offset = { 'Monday':0,'Tuesday':1,'Wednesday':2,'Thursday':3,'Friday':4,'Saturday':5,'Sunday':6 }

            for m in meal_plan['meals']:
                meal_day = m['day']
                meal_plan_meal_id = m['meal_plan_meal_id']
                meal_date = selected_week_start + timedelta(days=day_offset[meal_day])
                meal_plan_records.append({
                    'Select': False,
                    'Meal Plan ID': meal_plan_id,
                    'Meal Plan Meal ID': meal_plan_meal_id,
                    'meal_id': m['meal']['id'],
                    'Meal Date': meal_date.strftime('%Y-%m-%d'),
                    'Meal Name': m['meal']['name'],
                    'Day': meal_day,
                    'Meal Type': m['meal_type'],
                    'Description': m['meal']['description'],
                })

            if not meal_plan_records:
                st.info("No meals found for this week.")
                return

            meal_plan_df = pd.DataFrame(meal_plan_records)
            if selected_day != "All Days":
                meal_plan_df = meal_plan_df[meal_plan_df['Day'] == selected_day]

            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            meal_type_order = ['Breakfast','Lunch','Dinner']
            meal_plan_df['Day'] = pd.Categorical(meal_plan_df['Day'], categories=day_order, ordered=True)
            meal_plan_df['Meal Type'] = pd.Categorical(meal_plan_df['Meal Type'], categories=meal_type_order, ordered=True)
            meal_plan_df = meal_plan_df.sort_values(['Day', 'Meal Type'])

            display_df = meal_plan_df.drop(columns=['Meal Plan ID', 'Meal Plan Meal ID', 'meal_id'])
            display_df = display_df[['Select','Day','Meal Type','Meal Name','Description','Meal Date']]

            selected_rows = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Select": st.column_config.CheckboxColumn(required=True),
                },
            )

            selected_indices = selected_rows[selected_rows['Select']].index.to_list()
            selected_data_full = meal_plan_df.iloc[selected_indices] if selected_indices else pd.DataFrame()

            # Determine the default tab based on action
            tab_names = ["Meals & Actions", "Meal Plan Reviews", "Meal Reviews"]
            default_tab_index = 0
            if action == 'review_meal' and meal_plan_id_from_url and meal_id_from_url:
                # If conditions are met, default to "Meal Reviews"
                default_tab_index = 2

            # Use a radio to simulate tabs with a default index
            selected_tab = st.radio("Sections", tab_names, index=default_tab_index)

            show_normal_ui(
                meal_plan_df, meal_plan_id, is_approved, is_past_week, selected_data_full,
                meal_plan_id_from_url, meal_id_from_url, action, selected_tab
            )

        else:
            logging.error(f"Failed to fetch meal plans. Status code: {response.status_code}, Response: {response.text}")
            st.error("Error fetching meal plans.")


    elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
        st.warning("Your email is not confirmed. Please confirm your email.")
        if st.button("Resend Activation Link"):
            resend_activation_link(st.session_state['user_id'])
    else:
        pass


def show_normal_ui(meal_plan_df, meal_plan_id, is_approved, is_past_week, selected_data_full,
                   meal_plan_id_from_url=None, meal_id_from_url=None, action=None, selected_tab=None):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    current_meal_prep_pref = st.session_state.get('meal_prep_preference', 'daily')

    # Meals & Actions Section
    if selected_tab == "Meals & Actions":
        st.write("### Actions for Selected Meals")
        colA, colB = st.columns(2)
        with colA:
            if st.button('Change Selected Meals', disabled=is_past_week):
                if selected_data_full.empty:
                    st.error("No meals selected. Please select meals first.")
                else:
                    meal_plan_id_selected = selected_data_full['Meal Plan ID'].iloc[0]
                    old_meal_ids = selected_data_full['meal_id'].tolist()
                    days_of_meal = selected_data_full['Day'].tolist()
                    meal_types = selected_data_full['Meal Type'].tolist()
                    preferred_language = st.session_state.user_info.get('preferred_language', 'English')
                    user_details_prompt = (
                        f"Consider the following user details:\n"
                        f"- Preferred language: {preferred_language}\n"
                        f"- Meal plan id: {meal_plan_id_selected}\n"
                        f"- Current/old meal id(s): {', '.join(map(str, old_meal_ids))}\n"
                        f"- Day(s) of the meal: {', '.join(days_of_meal)}\n"
                        f"- Meal type(s): {', '.join(meal_types)}\n"
                    )
                    prompt = "Please change the selected meal(s)"
                    user_id = st.session_state.get('user_id')
                    try:
                        resp = chat_with_gpt(user_details_prompt, st.session_state.thread_id, user_id=user_id) if is_user_authenticated() else guest_chat_with_gpt(user_details_prompt, st.session_state.thread_id)
                    except Exception as e:
                        st.error("Failed to communicate with the assistant. Please try again.")
                        logging.error(f"Assistant communication error: {e}")
                        return
                    if resp and 'new_thread_id' in resp:
                        logging.info(f"New thread ID: {resp['new_thread_id']}")
                        st.session_state.thread_id = resp['new_thread_id']
                    start_or_continue_streaming(
                        client, 
                        user_id=st.session_state.user_info['user_id'], 
                        openai_headers=openai_headers, 
                        chat_container=None, 
                        user_details_prompt=user_details_prompt, 
                        prompt=prompt, 
                        change_meals=True
                    )
                    st.rerun()

            if st.button('Approve Meal Plan', disabled=is_past_week):
                if not meal_plan_df.empty:
                    user_id = int(st.session_state.user_info['user_id'])
                    payload = {'user_id':user_id,'meal_plan_id':meal_plan_id}
                    with st.spinner("Approving meal plan..."):
                        resp = api_call_with_refresh(
                            url=f"{os.getenv('DJANGO_URL')}/meals/api/approve_meal_plan/",
                            method='post',
                            headers=headers,
                            data=payload
                        )
                    if resp.status_code == 200:
                        res = resp.json()
                        if res['status'] == 'success':
                            st.success(res['message'])
                            if 'order_id' in res:
                                st.info(f"Order ID: {res['order_id']} - Proceed to payment.")
                            st.rerun()
                        else:
                            st.info(res['message'])
                    else:
                        st.error("Failed to approve meal plan.")
                else:
                    st.error("No meal plans found for approval.")

        with colB:
            if current_meal_prep_pref == 'daily':
                if st.button('Generate Cooking Instructions'):
                    if selected_data_full.empty:
                        st.error("Select meals first.")
                    else:
                        meal_plan_meal_ids = selected_data_full['Meal Plan Meal ID'].tolist()
                        if meal_plan_meal_ids:
                            payload = {'meal_plan_meal_ids': meal_plan_meal_ids}
                            with st.spinner("Generating cooking instructions..."):
                                gen_resp = api_call_with_refresh(
                                    url=f"{os.getenv('DJANGO_URL')}/meals/api/generate_cooking_instructions/",
                                    method='post',
                                    headers=headers,
                                    data=payload
                                )
                            if gen_resp.status_code == 200:
                                st.success("Cooking instructions generation initiated.")
                                with st.spinner("Fetching cooking instructions..."):
                                    fetch_resp = api_call_with_refresh(
                                        url=f"{os.getenv('DJANGO_URL')}/meals/api/fetch_instructions/?meal_plan_meal_ids=" + ','.join(map(str, meal_plan_meal_ids)),
                                        method='get',
                                        headers=headers,
                                    )
                                if fetch_resp.status_code == 200:
                                    st.session_state['instructions'] = fetch_resp.json().get('instructions', [])
                                    if st.session_state['instructions']:
                                        display_instructions_pagination()
                                    else:
                                        st.info("No instructions available yet. Please check back later.")
                                else:
                                    st.error("Error fetching instructions.")
                            else:
                                st.error("Error generating instructions.")
                        else:
                            st.error("No valid meal IDs found.")
            else:
                if st.button('View Bulk Prep Instructions'):
                    if not meal_plan_df.empty:
                        meal_plan_id_bulk = int(meal_plan_df['Meal Plan ID'].iloc[0])
                        with st.spinner("Fetching bulk prep instructions..."):
                            bulk_resp = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/meals/api/fetch_instructions/?meal_plan_id={meal_plan_id_bulk}",
                                method='get',
                                headers=headers,
                            )
                        if bulk_resp.status_code == 200:
                            resp_data = bulk_resp.json()
                            st.session_state['instructions'] = resp_data.get('instructions', [])
                            st.session_state['meal_prep_preference'] = resp_data.get('meal_prep_preference', 'one_day_prep')
                            if st.session_state['instructions']:
                                display_instructions_pagination()
                            else:
                                st.info("No instructions available yet. Please check back later.")
                        else:
                            st.error("Error fetching bulk prep instructions.")
                    else:
                        st.error("No meal plan found.")

        st.markdown("---")

        if st.button('Delete Selected Meals'):
            if selected_data_full.empty:
                st.error("No meals selected.")
            else:
                meal_plan_meal_ids = selected_data_full['Meal Plan Meal ID'].tolist()
                if meal_plan_meal_ids:
                    payload = {'meal_plan_meal_ids': meal_plan_meal_ids}
                    with st.spinner("Deleting selected meals..."):
                        del_resp = api_call_with_refresh(
                            url=f'{os.getenv("DJANGO_URL")}/meals/api/remove_meal_from_plan/',
                            method='delete',
                            headers=headers,
                            data=payload
                        )
                    if del_resp.status_code == 200:
                        st.success("Selected meals deleted successfully.")
                        st.rerun()
                    else:
                        st.error("Failed to delete selected meals.")
                else:
                    st.error("No valid meal IDs found.")

        if 'instructions' in st.session_state and st.session_state['instructions']:
            display_instructions_pagination()

    elif selected_tab == "Meal Plan Reviews":
        st.write("### Meal Plan Reviews")
        if is_approved:
            rev_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal_plan/{meal_plan_id}/reviews/",
                method='get',
                headers=headers
            )
            if rev_resp.status_code == 200:
                rev_data = rev_resp.json()
                if not rev_data:
                    st.info("No reviews yet.")
                else:
                    for r in rev_data:
                        st.markdown(f"**Rating:** {r['rating']}/5\n**Comment:** {r['comment']}")
                        st.markdown("---")
            else:
                st.error("Failed to fetch meal plan reviews.")

            rating = st.slider("Rating", 1, 5, 5)
            comment = st.text_area("Comment for Meal Plan")
            if st.button("Submit Meal Plan Review"):
                payload = {"rating": rating, "comment": comment}
                rev_post = api_call_with_refresh(
                    url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal_plan/{meal_plan_id}/review/",
                    method='post',
                    headers=headers,
                    data=payload
                )
                if rev_post.status_code == 201:
                    st.success("Review submitted!")
                    st.experimental_rerun()
                else:
                    st.error("Failed to submit review.")
        else:
            st.info("Meal plan not approved yet. Approve it first to leave a review.")

    elif selected_tab == "Meal Reviews":
        st.write("### Meal Reviews")
        if is_approved:
            # 1) Let the user select a meal.
            unique_meals = meal_plan_df[['meal_id','Meal Name']].drop_duplicates()

            meal_index = 0
            if action == 'review_meal' and meal_plan_id_from_url and meal_id_from_url:
                if int(meal_plan_id_from_url) == meal_plan_id and not meal_plan_df[meal_plan_df['meal_id'] == int(meal_id_from_url)].empty:
                    meal_id_list = unique_meals['meal_id'].tolist()
                    if int(meal_id_from_url) in meal_id_list:
                        meal_index = meal_id_list.index(int(meal_id_from_url))

            meal_selection = st.selectbox(
                "Select a Meal to Review", 
                options=unique_meals['Meal Name'], 
                index=meal_index
            )
            selected_meal_id = unique_meals[unique_meals['Meal Name'] == meal_selection]['meal_id'].values[0]

            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            user_id = st.session_state.user_info["user_id"]  # Adjust if needed

            # -------------------------------------------------------------
            # 2) Fetch any existing review for this user + meal
            # -------------------------------------------------------------
            existing_review = None
            review_fetch_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal/{selected_meal_id}/reviews/",
                method='get',
                headers=headers,
            )
            if review_fetch_resp.status_code == 200:
                all_meal_reviews = review_fetch_resp.json()  # list of reviews
                # Find a review where review['user'] matches our current user ID
                for r in all_meal_reviews:
                    # Depending on how your serializer is set up, 
                    # you might need to compare r['user'] == user_id or r['user']['id'] == user_id, etc.
                    if r['user'] == user_id:
                        existing_review = r
                        break
            else:
                st.warning("Could not load reviews for this meal.")

            # -------------------------------------------------------------
            # 3) Display rating/comment, pre-filled if there's an existing review
            # -------------------------------------------------------------
            if existing_review:
                st.info("You have already submitted a review for this meal. Update it below.")
                default_rating = existing_review.get('rating', 5)
                default_comment = existing_review.get('comment', '')
            else:
                default_rating = 5
                default_comment = ''

            meal_rating = st.slider("Meal Rating", 1, 5, default_rating)
            meal_comment = st.text_area("Comment for Meal", default_comment)

            # -------------------------------------------------------------
            # 4) One button to post your review (create or update)
            # -------------------------------------------------------------
            if st.button("Submit Meal Review"):
                payload = {
                    "rating": meal_rating,
                    "comment": meal_comment,
                    "meal_plan_id": meal_plan_id
                }
                meal_rev_post = api_call_with_refresh(
                    url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal/{selected_meal_id}/review/",
                    method='post',  # same endpoint for both create & update
                    headers=headers,
                    data=payload
                )

                # The endpoint returns 201 if created, 200 if updated
                if meal_rev_post.status_code in (200, 201):
                    if meal_rev_post.status_code == 201:
                        st.success("Meal review created!")
                    else:
                        st.success("Meal review updated!")
                else:
                    st.error(f"Failed to submit meal review. Status code: {meal_rev_post.status_code}")

        else:
            st.info("Meal plan is not approved yet. Approve it first to leave individual meal reviews.")

@st.fragment
def display_instructions_pagination():
    instructions = st.session_state.get('instructions', [])
    meal_prep_preference = st.session_state.get('meal_prep_preference', 'daily')

    if not instructions:
        st.error("No instructions available.")
        return

    instruction_options = []
    for idx, instruction_item in enumerate(instructions):
        instruction_type = instruction_item.get('instruction_type', 'Unknown')
        date = instruction_item.get('date', 'No Date')
        if instruction_type == 'bulk_prep':
            option_label = "Bulk Prep Instructions"
        elif instruction_type == 'follow_up':
            option_label = f"Follow-Up Instructions for {date}"
        elif instruction_type == 'daily':
            meal_name = instruction_item.get('meal_name', 'Unknown Meal')
            option_label = f"{meal_name} - {date}"
        else:
            option_label = f"Instructions {idx}"
        instruction_options.append((idx, option_label))

    selected_idx = st.selectbox(
        "Select Instructions",
        options=[i for i,_ in instruction_options],
        format_func=lambda i: instruction_options[i][1]
    )

    selected_instruction = instructions[selected_idx]
    instructions_json_str = selected_instruction.get('instructions')
    instruction_type = selected_instruction.get('instruction_type', 'Unknown')

    if instructions_json_str:
        try:
            instructions_data = json.loads(instructions_json_str)
            if instruction_type == 'bulk_prep':
                if isinstance(instructions_data, dict):
                    bulk_prep_steps = instructions_data.get('bulk_prep_steps', [])
                elif isinstance(instructions_data, list):
                    bulk_prep_steps = instructions_data
                else:
                    st.error("Unexpected format of bulk prep instructions.")
                    return
                st.subheader("Bulk Meal Prep Instructions")
                for step in bulk_prep_steps:
                    step_number = step.get('step_number', 'N/A')
                    description = step.get('description', 'No description provided.')
                    duration = step.get('duration', 'N/A')
                    ingredients_list = step.get('ingredients', [])
                    ingredients = ', '.join(ingredients_list) if ingredients_list else 'N/A'
                    st.markdown(f"**Step {step_number}:** {description}")
                    st.markdown(f"**Duration:** {duration}")
                    st.markdown(f"**Ingredients:** {ingredients}")
                    st.markdown("---")

            elif instruction_type == 'follow_up':
                if isinstance(instructions_data, dict):
                    tasks = instructions_data.get('tasks', [])
                    day = instructions_data.get('day', selected_instruction.get('date', 'Unknown Day'))
                    total_estimated_time = instructions_data.get('total_estimated_time', 'N/A')
                elif isinstance(instructions_data, list):
                    tasks = instructions_data
                    day = selected_instruction.get('date', 'Unknown Day')
                    total_estimated_time = 'N/A'
                else:
                    st.error("Unexpected format of follow-up instructions.")
                    return
                st.subheader(f"Follow-Up Instructions for {day}")
                st.markdown(f"**Total Estimated Time:** {total_estimated_time}")
                st.markdown("---")
                for task in tasks:
                    step_number = task.get('step_number', 'N/A')
                    description = task.get('description', 'No description provided.')
                    duration = task.get('duration', 'N/A')
                    st.markdown(f"**Step {step_number}:** {description}")
                    st.markdown(f"**Duration:** {duration}")
                    st.markdown("---")

            elif instruction_type == 'daily':
                steps = instructions_data.get('steps', [])
                meal_name = selected_instruction.get('meal_name', 'Unknown Meal')
                st.subheader(f"Instructions for {meal_name} on {selected_instruction.get('date', 'Unknown Date')}")
                for step in steps:
                    step_number = step.get('step_number', 'Unknown')
                    description = step.get('description', 'No description available')
                    duration = step.get('duration', 'No duration')
                    st.markdown(f"**Step {step_number}:** {description}")
                    st.markdown(f"**Duration:** {duration}")
                    st.markdown("---")
            else:
                st.error("Unknown instruction type.")
        except Exception as e:
            st.error("Failed to parse instructions.")
            logging.error(f"Parsing error: {e}")
    else:
        st.warning("Instructions not yet available.")



if __name__ == "__main__":
    meal_plans()