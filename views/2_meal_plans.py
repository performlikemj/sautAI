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
import time
import re

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

def fetch_gamification_data():
    """Fetch gamification data from Django backend."""
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = requests.get(
            f"{os.getenv('DJANGO_URL')}/gamification/api/streamlit-data/", 
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Update session state
            st.session_state.meal_plan_streak = data.get('meal_plan_streak', 0)
            st.session_state.total_meals_planned = data.get('total_meals_planned', 0)
            st.session_state.user_level = data.get('user_level', "Apprentice Chef")
            st.session_state.points = data.get('points', 0)
            
            # Weekly goal data
            weekly_goal = data.get('weekly_goal', {})
            st.session_state.weekly_goal_progress = weekly_goal.get('progress', 0.0)
            st.session_state.weekly_goal_text = weekly_goal.get('text', "0/7 days planned")
            
            # Check for new achievements
            new_achievements = data.get('new_achievements', [])
            if new_achievements:
                # Handle new achievements (add notifications or celebrations)
                for achievement in new_achievements:
                    st.balloons()
                    st.success(f"🏆 New Achievement: {achievement['name']} - {achievement['description']}")
                    
            return True
        else:
            logging.error(f"Failed to fetch gamification data: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error fetching gamification data: {str(e)}")
        return False

def fetch_leaderboard():
    """Fetch leaderboard data from the backend."""
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = requests.get(
            f"{os.getenv('DJANGO_URL')}/gamification/api/leaderboard/", 
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json().get('leaderboard', [])
        else:
            logging.error(f"Failed to fetch leaderboard: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error fetching leaderboard: {str(e)}")
        return []

def trigger_gamification_event(event_type, details=None):
    """Trigger a gamification event in the Django backend."""
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        payload = {
            'event_type': event_type,
            'details': details or {}
        }
        response = requests.post(
            f"{os.getenv('DJANGO_URL')}/gamification/api/event/", 
            headers=headers,
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            # Refresh gamification data to show updated stats
            fetch_gamification_data()
            return True
        else:
            logging.error(f"Failed to trigger gamification event: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error triggering gamification event: {str(e)}")
        return False

def fetch_user_dietary_preferences():
    """Fetch the user's dietary preferences from the backend and update session state."""
    try:
        if 'user_info' in st.session_state and 'access' in st.session_state.user_info:
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            response = requests.get(
                f"{os.getenv('DJANGO_URL')}/meals/api/user-profile/",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Backend now returns dietary preferences with names
                user_preferences = []
                for pref in user_data.get('dietary_preferences', []):
                    if isinstance(pref, dict) and 'name' in pref:
                        user_preferences.append(pref['name'])
                
                # Update session state with the user's preferences
                st.session_state.user_dietary_preferences = user_preferences
                
                # If no filters are currently selected, use the user's default preferences
                if not st.session_state.dietary_preferences:
                    st.session_state.dietary_preferences = user_preferences.copy()
                
                return True
            else:
                logging.error(f"Failed to fetch user profile: {response.status_code}")
                return False
        return False
    except Exception as e:
        logging.error(f"Error fetching user profile: {str(e)}")
        return False

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
        format_func=lambda i: instruction_options[i][1],
        key="instruction_selector"
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

def show_normal_ui(meal_plan_df, meal_plan_id, is_approved, is_past_week, selected_data_full,
                   meal_plan_id_from_url=None, meal_id_from_url=None, action=None, selected_tab=None):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    current_meal_prep_pref = st.session_state.get('meal_prep_preference', 'daily')

    # This function now only shows tab-specific content, not the main actions
    if selected_tab == "📊 Overview":
        # Show overview information about the meal plan
        st.write("### 📊 Meal Plan Overview")
        
        # Show statistics if approved
        if is_approved:
            st.success("✅ This meal plan is approved")
            
            # Get meal count by type
            meal_types = meal_plan_df['Meal Type'].value_counts()
            
            # Display statistics in columns
            stat_cols = st.columns(3)
            with stat_cols[0]:
                st.metric("Total Meals", f"{len(meal_plan_df)} 🍽️")
            with stat_cols[1]:
                breakfast_count = meal_types.get('Breakfast', 0)
                st.metric("Breakfasts", f"{breakfast_count} 🍳")
            with stat_cols[2]:
                lunch_dinner_count = meal_types.get('Lunch', 0) + meal_types.get('Dinner', 0)
                st.metric("Lunch & Dinner", f"{lunch_dinner_count} 🥗")
                
            st.markdown("---")
            
            # Show meal prep preference
            st.info(f"🔄 **Meal Prep Preference**: {'Daily preparation' if current_meal_prep_pref == 'daily' else 'Bulk preparation'}")
            
        else:
            st.warning("⚠️ This meal plan is not yet approved")
            st.info("Approve your meal plan to unlock reviews and cooking instructions!")
            
        # Display any additional meal plan details or statistics here

    elif selected_tab == "⭐ Reviews":
        st.write("### ⭐ Meal Plan Reviews")
        if is_approved:
            # Display review statistics
            rev_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal_plan/{meal_plan_id}/reviews/",
                method='get',
                headers=headers
            )
            if rev_resp.status_code == 200:
                rev_data = rev_resp.json()
                if not rev_data:
                    st.info("🌟 Be the first to review this meal plan!")
                else:
                    # Calculate average rating
                    avg_rating = sum(r['rating'] for r in rev_data) / len(rev_data)
                    
                    # Display rating statistics
                    stats_cols = st.columns(3)
                    with stats_cols[0]:
                        st.metric("Average Rating", f"{avg_rating:.1f} ⭐")
                    with stats_cols[1]:
                        st.metric("Total Reviews", f"{len(rev_data)} 📝")
                    with stats_cols[2]:
                        five_stars = sum(1 for r in rev_data if r['rating'] == 5)
                        st.metric("5-Star Reviews", f"{five_stars} 🌟")

                    # Display reviews in a modern card layout
                    st.markdown("### Recent Reviews")
                    for r in rev_data:
                        with st.container():
                            st.markdown(f"""
                            <div style='padding: 1rem; border-radius: 0.5rem; background-color: #f0f2f6; margin-bottom: 1rem;'>
                                <h4>{'⭐' * r['rating']}</h4>
                                <p><em>{r['comment']}</em></p>
                            </div>
                            """, unsafe_allow_html=True)

            else:
                st.error("Failed to fetch meal plan reviews.")

            # Add review form with improved UI
            st.markdown("### ✍️ Write a Review")
            with st.form("review_form"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    rating = st.slider(
                        "Rating",
                        1, 5, 5,
                        help="How would you rate this meal plan?",
                        format="%d ⭐"
                    )
                with col2:
                    comment = st.text_area(
                        "Your Review",
                        placeholder="Share your experience with this meal plan...",
                        help="What did you like? What could be improved?"
                    )
                
                if st.form_submit_button("Submit Review", use_container_width=True):
                    if not comment.strip():
                        st.warning("Please add a comment to your review.")
                    else:
                        payload = {"rating": rating, "comment": comment}
                        with st.spinner("Submitting your review..."):
                            rev_post = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/reviews/api/meal_plan/{meal_plan_id}/review/",
                                method='post',
                                headers=headers,
                                data=payload
                            )
                            if rev_post.status_code == 201:
                                st.success("Thank you for your review! 🎉")
                                
                                # Trigger gamification event for submitting a meal review
                                trigger_gamification_event('meal_plan_reviewed', {
                                    'meal_plan_id': meal_plan_id,
                                    'rating': rating
                                })
                                
                                st.balloons()
                                # Fetch updated gamification data
                                fetch_gamification_data()
                                st.rerun()
                            else:
                                st.error("Failed to submit review.")
        else:
            st.info("📝 Approve your meal plan to start leaving reviews!")
            st.markdown("""
            #### Why Review?
            - Help others discover great meal combinations
            - Earn badges and rewards
            - Improve future meal suggestions
            - Build your foodie reputation!
            """)

    elif selected_tab == "📝 Meal Reviews":
        st.write("### 🍽️ Individual Meal Reviews")
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
                index=meal_index,
                key="meal_review_selector"
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
                    is_new = meal_rev_post.status_code == 201
                    st.success(f"Meal review {'created' if is_new else 'updated'}!")
                    
                    # Trigger gamification event for submitting a meal review
                    trigger_gamification_event('meal_reviewed', {
                        'meal_id': selected_meal_id,
                        'meal_plan_id': meal_plan_id,
                        'rating': meal_rating,
                        'is_new': is_new
                    })
                    
                    # Refresh gamification data
                    fetch_gamification_data()
                else:
                    st.error(f"Failed to submit meal review. Status code: {meal_rev_post.status_code}")

        else:
            st.info("Meal plan is not approved yet. Approve it first to leave individual meal reviews.")


# Initialize session state for gamification features
if 'meal_plan_streak' not in st.session_state:
    st.session_state.meal_plan_streak = 0
if 'total_meals_planned' not in st.session_state:
    st.session_state.total_meals_planned = 0
if 'user_level' not in st.session_state:
    st.session_state.user_level = "Apprentice Chef"
if 'points' not in st.session_state:
    st.session_state.points = 0
if 'weekly_goal_progress' not in st.session_state:
    st.session_state.weekly_goal_progress = 0.0
if 'weekly_goal_text' not in st.session_state:
    st.session_state.weekly_goal_text = "0/7 days planned"
if 'show_leaderboard' not in st.session_state:
    st.session_state.show_leaderboard = False
if 'dietary_preferences' not in st.session_state:
    st.session_state.dietary_preferences = []
# Add a list of all available dietary preferences
if 'all_dietary_preferences' not in st.session_state:
    st.session_state.all_dietary_preferences = [
        'Everything', 'Vegetarian', 'Vegan', 'Pescatarian', 'Gluten-Free', 'Keto', 
        'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 
        'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 
        'Diabetic-Friendly'
    ]

# Parse query parameters for email link scenario
meal_plan_id_from_url = st.query_params.get('meal_plan_id')
meal_id_from_url = st.query_params.get('meal_id')
action = st.query_params.get('action', None)

# Check for approval token (email approval flow)
approval_token = st.query_params.get('approval_token')
meal_prep_preference = st.query_params.get('meal_prep_preference', None)

if approval_token and meal_prep_preference:
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
    st.stop()

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
    st.stop()

# Create a welcome screen for users that aren't logged in
if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
    st.title("📅 SautAI Meal Plans")
    
    # Explain the benefits and features
    st.markdown("""
    ### Discover personalized meal plans tailored just for you!
    
    With SautAI's powerful meal planning features, you can:
    - Get AI-generated meal plans based on your dietary preferences
    - Easily approve and customize your weekly meals
    - Generate detailed cooking instructions
    - Track your nutrition goals
    - And much more!
    """)
    
    # Add some visually appealing images or stats
    cols = st.columns(3)
    with cols[0]:
        st.metric("Average Meals Per Week", "21")
    with cols[1]:
        st.metric("Dietary Options", "18+")

    
    st.markdown("---")
    
    # Show login/registration options
    st.subheader("Ready to start your personalized meal planning journey?")
    
    login_cols = st.columns([1,1])
    with login_cols[0]:
        if st.button("Login Now", type="primary", use_container_width=True):
            login_form()
            st.stop()
    with login_cols[1]:
        if st.button("Create Account", use_container_width=True):
            # In Streamlit, redirect to the register page
            # For Streamlit, we'd normally use st.switch_page but since it's not an exact fit for navigation,
            # we'll use this workaround with JavaScript
            st.markdown("""
            <script>
            const params = new URLSearchParams();
            params.set('from_meal_plans', 'true');
            window.location.href = '/Register?' + params.toString();
            </script>
            """, unsafe_allow_html=True)
            st.info("Redirecting to registration page...")
    
    # Sample preview (optional)
    with st.expander("See a sample meal plan"):
        st.markdown("""
        ### Sample Weekly Meal Plan
        
        #### Monday
        - 🍳 **Breakfast**: Avocado Toast with Poached Eggs
        - 🥗 **Lunch**: Mediterranean Quinoa Salad
        - 🍽️ **Dinner**: Herb-Roasted Salmon with Vegetables
        
        #### Tuesday
        - 🍳 **Breakfast**: Greek Yogurt with Fresh Berries and Honey
        - 🥗 **Lunch**: Chicken and Vegetable Wrap
        - 🍽️ **Dinner**: Vegetable Stir-Fry with Brown Rice
        
        *Create an account to see your own personalized meal plans!*
        """)
    
    st.markdown("---")
    st.info("Already have a meal plan sent to you via email? Check your inbox for approval links!")
    
    # Stop execution here for non-logged in users
    st.stop()

# Display logout button and chef mode toggle if user is logged in
if st.button("Logout", key='meal_plan_logout'):
    # Clear session state but preserve navigation
    navigation_state = st.session_state.get("navigation", None)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if navigation_state:
        st.session_state["navigation"] = navigation_state
    st.success("Logged out successfully!")
    st.rerun()

# Toggle chef mode
toggle_chef_mode()

# Check if user is authenticated and email confirmed
if is_user_authenticated() and st.session_state.get('email_confirmed', False):
    # Fetch gamification data from backend
    fetch_gamification_data()
    
    if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
        # Create a sidebar for filters and user stats
        with st.sidebar:
            st.title("🏆 Your Progress")
            st.metric("Meal Planning Streak", f"{st.session_state.meal_plan_streak} days")
            st.metric("Total Meals Planned", st.session_state.total_meals_planned)
            st.metric("Current Level", st.session_state.user_level)
            st.metric("Points", st.session_state.points)  # Add points display
            
            st.markdown("---")
            st.subheader("🎯 Weekly Goals")
            goals_complete = st.progress(
                st.session_state.weekly_goal_progress, 
                text=st.session_state.weekly_goal_text
            )
            st.markdown("Complete your week's plan to earn rewards!")
            
            # Add a refresh button
            if st.button("Refresh Progress"):
                fetch_gamification_data()
                st.success("Progress updated!")
            
            st.markdown("---")
            
            # Add leaderboard button
            if st.button("View Leaderboard"):
                st.session_state.show_leaderboard = not st.session_state.show_leaderboard
                st.rerun()
            
            if st.session_state.show_leaderboard:
                st.subheader("🏆 Leaderboard")
                leaderboard = fetch_leaderboard()
                
                if leaderboard:
                    leaderboard_data = []
                    for entry in leaderboard:
                        username = entry['username']
                        if entry.get('is_current_user', False):
                            username = f"👤 {username} (You)"
                            
                        leaderboard_data.append({
                            "Rank": entry['rank'],
                            "User": username,
                            "Level": entry['level'],
                            "Points": entry['points'],
                            "Streak": f"{entry.get('streak', 0)} days"
                        })
                    
                    st.dataframe(leaderboard_data, use_container_width=True, hide_index=True)
                else:
                    st.info("Leaderboard data not available.")
            
            st.markdown("---")
            st.subheader("⚙️ Preferences")
            meal_filters = st.multiselect(
                "Dietary Preferences",
                st.session_state.all_dietary_preferences,
                default=st.session_state.dietary_preferences,
                help="Filter your meal suggestions"
            )
            # Save preferences to session state when they change
            if meal_filters != st.session_state.dietary_preferences:
                st.session_state.dietary_preferences = meal_filters
                st.rerun()  # Refresh the page to apply filters
            
            # Add a Clear Filters button when filters are active
            if st.session_state.dietary_preferences:
                if st.button("Clear Filters", use_container_width=True):
                    st.session_state.dietary_preferences = []
                    st.rerun()

        # Main content area with improved layout
        st.title("📅 Your Meal Plans")
        welcome_col1, welcome_col2 = st.columns([2,1])
        if 'selected_week_start' not in st.session_state:
            st.session_state.selected_week_start = datetime.now().date() - timedelta(days=datetime.now().date().weekday())
        if 'selected_day' not in st.session_state:
            st.session_state.selected_day = "All Days"

        selected_week_start = st.session_state.selected_week_start
        selected_week_end = selected_week_start + timedelta(days=6)
        is_past_week = selected_week_end < datetime.now().date()
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        with welcome_col1:
            st.markdown("""
            ### Welcome to Your Personal Meal Planning Dashboard!
            Here you can create, customize, and optimize your weekly meal plans. Get personalized 
            suggestions based on your preferences and track your healthy eating journey.

            Need help? Contact support@sautai.com
            """)
        with welcome_col2:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                with st.spinner("Creating your personalized meal plan..."):
                    try:
                        # Client-side validation for past dates
                        today = datetime.now().date()
                        if selected_week_end < today:
                            st.error("⚠️ Cannot generate meal plans for past weeks. Please select a current or future week.")
                        else:
                            # Get the start date for the selected week
                            week_start_date = selected_week_start.strftime('%Y-%m-%d')
                            
                            # Call the meal plan generation endpoint
                            gen_resp = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/meals/api/generate_meal_plan/",
                                method='post',
                                headers=headers,
                                data={
                                    'week_start_date': week_start_date,
                                    'dietary_preferences': [pref for pref in st.session_state.dietary_preferences if pref != 'Everything']
                                }
                            )
                            if gen_resp.status_code == 201:
                                response_data = gen_resp.json()
                                st.success("✨ " + response_data.get('message', 'New meal plan generated!'))
                                
                                # Trigger gamification event
                                trigger_gamification_event('meal_plan_created', {
                                    'week_start_date': week_start_date,
                                    'meal_count': 21  # Or however many meals are in the plan
                                })
                                
                                st.balloons()
                                st.rerun()
                            elif gen_resp.status_code == 200:
                                # Handle existing meal plan (new response format)
                                response_data = gen_resp.json()
                                status = response_data.get('status')
                                message = response_data.get('message', '')
                                
                                if status == 'existing_plan':
                                    details = response_data.get('details', {})
                                    is_approved = details.get('is_approved', False)
                                    meal_plan_id = details.get('meal_plan_id')
                                    status_text = "approved" if is_approved else "pending approval"
                                    week_start = details.get('week_start_date')
                                    week_end = details.get('week_end_date')
                                    meal_count = details.get('meal_count', 0)
                                    action_required = details.get('action_required', 'View your existing plan above.')
                                    
                                    st.warning(f"""
                                    ℹ️ You already have a meal plan for this week ({status_text}).
                                    
                                    • Week: {week_start} to {week_end}
                                    • Meals: {meal_count} meals in your plan
                                    
                                    {action_required}
                                    """)
                                   
                                else:
                                    # Handle other 200 responses
                                    st.info(message or 'Operation completed successfully.')
                                    st.rerun()
                            elif gen_resp.status_code == 400:
                                response_data = gen_resp.json()
                                status = response_data.get('status', 'error')
                                message = response_data.get('message', 'Failed to generate plan')
                                details = response_data.get('details', {})

                                if "past weeks" in message.lower():
                                    # New format for past weeks error
                                    current_date = datetime.strptime(details.get('current_date', today.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
                                    provided_date = datetime.strptime(details.get('provided_date', selected_week_start.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
                                    
                                    st.error(f"""
                                    ⚠️ Cannot generate meal plans for past weeks.
                                    
                                    • Current date: {current_date.strftime('%B %d, %Y')}
                                    • Selected week: {provided_date.strftime('%B %d, %Y')}
                                    
                                    Please select a week starting from today or later.
                                    """)
                                    
                                elif "no suitable meals" in message.lower():
                                    # Enhanced error handling for no suitable meals
                                    dietary_prefs = details.get('dietary_preferences', [])
                                    possible_reasons = details.get('possible_reasons', [])
                                    
                                    # Format reasons as bullet points
                                    reasons_list = "\n".join([f"• {reason}" for reason in possible_reasons])
                                    
                                    st.warning(f"""
                                    😔 Unable to generate a complete meal plan.
                                    
                                    • Your dietary preferences: {', '.join(dietary_prefs) if dietary_prefs else 'None set'}
                                    
                                    Possible reasons:
                                    {reasons_list}
                                    
                                    {details.get('suggestion', 'Try adjusting your dietary preferences or selecting a different week.')}
                                    """)
                                    
                                else:
                                    # General error handling
                                    st.error(f"⚠️ {message}")
                                    
                                    # If there are detailed reasons or suggestions, show them
                                    if isinstance(details, dict) and details:
                                        for key, value in details.items():
                                            if key != 'suggestion' and value:  # Handle suggestion separately
                                                if isinstance(value, list):
                                                    formatted_value = "\n".join([f"• {item}" for item in value])
                                                    st.info(f"**{key.replace('_', ' ').title()}**:\n{formatted_value}")
                                                else:
                                                    st.info(f"**{key.replace('_', ' ').title()}**: {value}")
                                        
                                        # Show suggestion as a helpful tip
                                        if 'suggestion' in details and details['suggestion']:
                                            st.info(f"💡 **Suggestion**: {details['suggestion']}")
                                    elif isinstance(details, str) and details:
                                        st.info(f"Details: {details}")
                                                
                                    time.sleep(2)  # Give time for the message to be read
                                    
                            else:
                                st.error("❌ Failed to generate meal plan. Please try again later.")
                                
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
                        logging.error(f"Error generating meal plan: {str(e)}")
                        logging.error(traceback.format_exc())
                        time.sleep(2)  # Give time for the error message to be read
                        st.rerun()

        st.markdown("---")

        # Week navigation with improved UI
        st.markdown("### 📅 Week Navigation")
        nav_cols = st.columns([1, 2, 1])
        with nav_cols[0]:
            if st.button('◀️ Previous Week', use_container_width=True):
                st.session_state.selected_week_start -= timedelta(weeks=1)
                st.session_state.selected_day = "All Days"
                st.rerun()
        with nav_cols[1]:
            st.markdown(f"<h3 style='text-align: center;'>{selected_week_start.strftime('%B %d')} - {selected_week_end.strftime('%B %d, %Y')}</h3>", unsafe_allow_html=True)
        with nav_cols[2]:
            if st.button('Next Week ▶️', use_container_width=True):
                st.session_state.selected_week_start += timedelta(weeks=1)
                st.session_state.selected_day = "All Days"
                st.rerun()

        # Day selection with visual calendar
        st.markdown("### 📆 Select Day")
        day_cols = st.columns(7)
        days_of_week = [(selected_week_start + timedelta(days=i)).strftime('%A') for i in range(7)]
        dates = [(selected_week_start + timedelta(days=i)).strftime('%d') for i in range(7)]
        
        # Initialize selected_day from session state
        selected_day = st.session_state.selected_day
        
        for i, (day, date) in enumerate(zip(days_of_week, dates)):
            with day_cols[i]:
                if st.button(
                    f"{day}\n{date}",
                    key=f"day_btn_{i}",
                    use_container_width=True,
                    type="secondary" if day != selected_day else "primary"
                ):
                    selected_day = day
                    st.session_state.selected_day = day
                    st.rerun()

        # Add an "All Days" option
        if st.button("👀 View All Days", use_container_width=True, type="secondary" if "All Days" != selected_day else "primary"):
            selected_day = "All Days"
            st.session_state.selected_day = "All Days"
            st.rerun()

        st.markdown("---")

        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/meal_plans/?week_start_date={selected_week_start}',
            method='get',
            headers=headers,
        )
        logging.info(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            meal_plan_data = response.json()
            if not meal_plan_data:
                st.info("No meals found for this week.")
                st.stop()

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
                    'Meal Date': pd.to_datetime(meal_date).date(),  # Convert to pandas datetime
                    'Meal Name': m['meal']['name'],
                    'Day': meal_day,
                    'Meal Type': m['meal_type'],
                    'Description': m['meal']['description'],
                })

            if not meal_plan_records:
                st.info("No meals found for this week.")
                st.stop()

            meal_plan_df = pd.DataFrame(meal_plan_records)
            if selected_day != "All Days":
                meal_plan_df = meal_plan_df[meal_plan_df['Day'] == selected_day]

            # Apply dietary preference filters if any are selected
            if st.session_state.dietary_preferences:
                # Skip filtering if 'Everything' is selected
                if 'Everything' in st.session_state.dietary_preferences:
                    # If 'Everything' is selected along with other filters, show a note
                    if len(st.session_state.dietary_preferences) > 1:
                        st.info("'Everything' option is selected, showing all meals regardless of other filters.")
                else:
                    # Get detailed meal data to check dietary attributes
                    filtered_meal_ids = []
                    
                    # Get unique meal IDs to minimize API calls
                    unique_meal_ids = meal_plan_df['meal_id'].unique().tolist()
                    missing_meals = []
                    
                    for meal_id in unique_meal_ids:
                        try:
                            meal_detail_resp = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/meals/api/meals/{meal_id}/",
                                method='get',
                                headers=headers
                            )
                            
                            if meal_detail_resp and hasattr(meal_detail_resp, 'status_code'):
                                if meal_detail_resp.status_code == 200:
                                    meal_detail = meal_detail_resp.json()
                                    # Get meal preferences by name
                                    meal_preferences = []
                                    
                                    # Handle various response formats
                                    dietary_preferences = meal_detail.get('dietary_preferences', [])
                                    if dietary_preferences:
                                        if isinstance(dietary_preferences[0], dict):
                                            # If preferences are objects with 'name' field
                                            meal_preferences = [pref['name'] for pref in dietary_preferences if 'name' in pref]
                                        elif isinstance(dietary_preferences[0], str):
                                            # If preferences are already strings
                                            meal_preferences = dietary_preferences
                                    
                                    # Check if all selected preferences match this meal
                                    matches_all_preferences = all(
                                        preference in meal_preferences
                                        for preference in st.session_state.dietary_preferences
                                    )
                                    
                                    if matches_all_preferences:
                                        filtered_meal_ids.append(meal_id)
                                elif meal_detail_resp.status_code == 404:
                                    # Track missing meals but don't log errors for 404s
                                    missing_meals.append(meal_id)
                            else:
                                # Handle case where response is None or doesn't have status_code
                                missing_meals.append(meal_id)
                        except Exception as e:
                            # More graceful error handling
                            missing_meals.append(meal_id)
                            logging.warning(f"Error fetching meal details for meal {meal_id}: {str(e)}")
                    
                    # Provide feedback if there were missing meals
                    if missing_meals and not filtered_meal_ids:
                        st.warning(
                            f"Some meal details ({len(missing_meals)} meals) could not be retrieved from the server. "
                            "Dietary preference filtering may not be accurate."
                        )
                        # Fallback: if no meals match or all had errors, show all meals
                        filtered_meal_ids = unique_meal_ids
                    
                    # Filter the DataFrame to show only meals that match all preferences
                    if filtered_meal_ids:
                        meal_plan_df = meal_plan_df[meal_plan_df['meal_id'].isin(filtered_meal_ids)]
                    else:
                        st.info(f"No meals match all selected dietary preferences: {', '.join(st.session_state.dietary_preferences)}")

            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            meal_type_order = ['Breakfast','Lunch','Dinner']
            meal_plan_df['Day'] = pd.Categorical(meal_plan_df['Day'], categories=day_order, ordered=True)
            meal_plan_df['Meal Type'] = pd.Categorical(meal_plan_df['Meal Type'], categories=meal_type_order, ordered=True)
            meal_plan_df = meal_plan_df.sort_values(['Day', 'Meal Type'])

            # Configure column display
            column_config = {
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select meals to perform actions",
                    required=True
                ),
                "Meal Name": st.column_config.Column(
                    "Meal",
                    help="Click to view meal details",
                    width="medium"
                ),
                "Description": st.column_config.TextColumn(
                    "Description",
                    help="Meal description and ingredients",
                    width="large"
                ),
                "Meal Date": st.column_config.Column(  # Changed from DateColumn to regular Column
                    "Date",
                    help="Scheduled date",
                    width="small"
                ),
                "Day": st.column_config.Column(
                    "Day of Week",
                    help="Day of the week",
                    width="small"
                ),
                "Meal Plan Meal ID": st.column_config.Column(
                    "Meal Plan Meal ID",
                    help="Internal ID",
                    width="small",
                    disabled=True
                )
            }

            # Keep Meal Plan Meal ID in the display DataFrame but hide it from view
            display_df = meal_plan_df.drop(columns=['Meal Plan ID', 'meal_id'])
            display_df = display_df[['Select', 'Day', 'Meal Type', 'Meal Name', 'Description', 'Meal Date', 'Meal Plan Meal ID']]

            # Add meal type icons
            meal_type_icons = {
                'Breakfast': '🍳',
                'Lunch': '🥗',
                'Dinner': '🍽️'
            }
            display_df['Meal Type'] = display_df['Meal Type'].apply(lambda x: f"{meal_type_icons.get(x, '')} {x}")

            # Configure the Meal Plan Meal ID column to be disabled (read-only)
            column_config["Meal Plan Meal ID"] = st.column_config.Column(
                "Meal Plan Meal ID",
                help="Internal ID",
                width="small",
                disabled=True
            )

            selected_rows = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config=column_config,
                column_order=["Select", "Day", "Meal Type", "Meal Name", "Description", "Meal Date"]
            )

            # Get the selected rows correctly
            selected_data_full = selected_rows[selected_rows['Select'] == True].copy()

            # Action buttons with improved UI
            st.markdown("### 🎯 Actions")
            
            # Initialize active_section if not present
            if 'active_section' not in st.session_state:
                st.session_state.active_section = None
            
            # Show appropriate section based on active_section
            if st.session_state.active_section == 'cooking_instructions' and 'instructions' in st.session_state and st.session_state['instructions']:
                st.markdown("### 👨‍🍳 Cooking Instructions")
                if st.button("⬅️ Back to Meals", key="back_from_instructions"):
                    st.session_state.active_section = None
                    st.rerun()
                display_instructions_pagination()
                
            elif st.session_state.active_section == 'approval_options':
                st.markdown("### ✅ Approve Meal Plan")
                if st.button("⬅️ Back to Meals", key="back_from_approval"):
                    st.session_state.active_section = None
                    st.rerun()
                    
                st.markdown("Choose how you would like to prepare your meals:")
                
                prep_preference = st.radio(
                    "Meal Preparation Method:",
                    ["daily", "one_day_prep"],
                    format_func=lambda x: "Daily Preparation (cook each meal fresh)" if x == "daily" else "Bulk Preparation (prepare multiple meals at once)",
                    key="approval_prep_preference"
                )
                
                approval_cols = st.columns(2)
                with approval_cols[0]:
                    if st.button("Confirm Approval", type="primary", key="confirm_approval_btn"):
                        user_id = st.session_state.user_info['user_id']
                        payload = {
                            'user_id': user_id,
                            'meal_plan_id': meal_plan_id,
                            'meal_prep_preference': prep_preference
                        }
                        
                        with st.spinner("Approving meal plan..."):
                            try:
                                approve_resp = api_call_with_refresh(
                                    url=f"{os.getenv('DJANGO_URL')}/meals/api/approve_meal_plan/",
                                    method='post',
                                    headers=headers,
                                    data=payload
                                )
                                
                                if approve_resp.status_code == 200:
                                    response_data = approve_resp.json()
                                    if response_data.get('status') == 'success':
                                        st.success(response_data.get('message', 'Meal plan approved successfully!'))
                                        
                                        # Trigger gamification event
                                        trigger_gamification_event('meal_plan_approved', {
                                            'meal_plan_id': meal_plan_id,
                                            'meal_prep_preference': prep_preference
                                        })
                                        
                                        st.balloons()
                                        if 'order_id' in response_data:
                                            st.info(f"Order created with ID: {response_data['order_id']}")
                                        st.session_state.active_section = None
                                        time.sleep(2)  # Give time to read the message
                                        st.rerun()
                                    else:
                                        st.error(response_data.get('message', 'Failed to approve meal plan'))
                                else:
                                    st.error(f"Error approving meal plan. Status code: {approve_resp.status_code}")
                            except Exception as e:
                                st.error(f"Error during meal plan approval: {str(e)}")
                                logging.error(f"Error approving meal plan: {str(e)}")
                                logging.error(traceback.format_exc())
                
                with approval_cols[1]:
                    if st.button("Cancel", key="cancel_approval_btn"):
                        st.session_state.active_section = None
                        st.rerun()
            
            elif st.session_state.active_section == 'edit_form':
                st.markdown("### ✏️ Edit Meals")
                if st.button("⬅️ Back to Meals", key="back_from_edit"):
                    st.session_state.active_section = None
                    st.rerun()
                    
                with st.form("edit_meals_form"):
                    meal_change_prompt = st.text_area(
                        "How would you like to change these meals?",
                        placeholder="e.g., 'Make them more vegetarian' or 'Include more protein'",
                        help="Describe your desired changes"
                    )
                    
                    if st.form_submit_button("Apply Changes", use_container_width=True):
                        if not meal_change_prompt.strip():
                            st.warning("Please describe the changes you'd like to make.")
                        else:
                            with st.spinner("Updating your meals..."):
                                try:
                                    # Get the meal plan meal IDs and dates from selected meals
                                    meal_plan_meal_ids = selected_data_full['Meal Plan Meal ID'].tolist()
                                    # Format dates directly since they're already datetime.date objects
                                    meal_dates = [date.strftime('%Y-%m-%d') for date in selected_data_full['Meal Date']]

                                    # Prepare payload for the API
                                    payload = {
                                        'meal_plan_meal_ids': meal_plan_meal_ids,
                                        'meal_dates': meal_dates,
                                        'prompt': meal_change_prompt.strip()
                                    }
                                    # Call the update endpoint
                                    update_resp = api_call_with_refresh(
                                        url=f"{os.getenv('DJANGO_URL')}/meals/api/update_meals_with_prompt/",
                                        method='post',
                                        headers=headers,
                                        data=payload
                                    )

                                    if update_resp.status_code == 200:
                                        response_data = update_resp.json()
                                        updates = response_data.get('updates', [])
                                        
                                        if updates:
                                            st.success("✨ Meals updated successfully!")
                                            
                                            # Trigger gamification event
                                            trigger_gamification_event('meals_updated', {
                                                'meal_count': len(updates),
                                                'meal_plan_id': meal_plan_id
                                            })
                                            
                                            for update in updates:
                                                old_meal = update.get('old_meal', {})
                                                new_meal = update.get('new_meal', {})
                                                was_generated = new_meal.get('was_generated', False)
                                                used_pantry_items = new_meal.get('used_pantry_items', [])
                                                
                                                # Create a detailed success message
                                                message = [
                                                    f"Changed '{old_meal.get('name', 'Unknown')}' to '{new_meal.get('name', 'Unknown')}'",
                                                    f"(New meal generated)" if was_generated else "(Alternative meal selected)"
                                                ]
                                                
                                                if used_pantry_items:
                                                    pantry_items_str = ", ".join(str(item) for item in used_pantry_items)
                                                    message.append(f"Used from your pantry: {pantry_items_str}")
                                                
                                                st.info("\n".join(message))
                                            
                                            st.session_state.active_section = None
                                            time.sleep(2)  # Give time to read the messages
                                            st.rerun()
                                        else:
                                            st.info("No changes were needed based on your request.")
                                        
                                    elif update_resp.status_code == 400:
                                        error_data = update_resp.json()
                                        error_msg = error_data.get('error', 'Invalid request data')
                                        st.error(f"⚠️ {error_msg}")
                                        
                                    elif update_resp.status_code == 404:
                                        error_data = update_resp.json()
                                        error_msg = error_data.get('error', 'No valid meals found for update')
                                        st.error(f"⚠️ {error_msg}")
                                        
                                    else:
                                        st.error("❌ Failed to update meals. Please try again.")
                                        if update_resp.text:
                                            st.error(f"Error details: {update_resp.text}")
                                
                                except Exception as e:
                                    st.error(f"❌ An error occurred: {str(e)}")
                                    logging.error(f"Error updating meals: {str(e)}")
                                    logging.error(traceback.format_exc())
                
                # Add a cancel button for the edit form
                if st.button("Cancel Editing", key="cancel_edit_btn"):
                    st.session_state.active_section = None
                    st.rerun()

            elif st.session_state.active_section == 'delete_confirmation':
                st.warning("Are you sure you want to delete the selected meals?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✓ Yes, Delete", type="primary", key="confirm_delete"):
                        meal_plan_meal_ids = selected_data_full['Meal Plan Meal ID'].tolist()
                        if meal_plan_meal_ids:
                            with st.spinner("Deleting selected meals..."):
                                del_resp = api_call_with_refresh(
                                    url=f"{os.getenv('DJANGO_URL')}/meals/api/remove_meal_from_plan/",
                                    method='delete',
                                    headers=headers,
                                    data={'meal_plan_meal_ids': meal_plan_meal_ids}  
                                )
                                if del_resp.status_code == 200:
                                    st.success("Selected meals deleted successfully!")
                                    st.session_state.active_section = None
                                    time.sleep(1)  # Give time for the success message
                                    st.rerun()
                                else:
                                    st.error(f"Failed to delete meals. Status: {del_resp.status_code}")
                                    if del_resp.text:
                                        st.error(f"Error: {del_resp.text}")
                with col2:
                    if st.button("✗ Cancel", key="cancel_delete"):
                        st.session_state.active_section = None
                        st.rerun()
            
            else:
                # Show action buttons only if no other section is active
                action_cols = st.columns(3)
                
                with action_cols[0]:
                    if st.button("👨‍🍳 Generate Cooking Instructions", use_container_width=True, disabled=is_past_week or selected_data_full.empty):
                        if selected_data_full.empty:
                            st.warning("Please select meals to generate cooking instructions")
                        else:
                            meal_plan_meal_ids = selected_data_full['Meal Plan Meal ID'].tolist()
                            with st.spinner("Generating cooking instructions..."):
                                try:
                                    # Call the backend to initiate instruction generation
                                    gen_resp = api_call_with_refresh(
                                        url=f"{os.getenv('DJANGO_URL')}/meals/api/generate_cooking_instructions/",
                                        method='post',
                                        headers=headers,
                                        data={'meal_plan_meal_ids': meal_plan_meal_ids}
                                    )
                                    
                                    if gen_resp.status_code == 200:
                                        st.success("Cooking instructions generation initiated!")
                                        # Fetch the instructions after they're generated
                                        fetch_resp = api_call_with_refresh(
                                            url=f"{os.getenv('DJANGO_URL')}/meals/api/fetch_instructions/?meal_plan_meal_ids=" + ','.join(map(str, meal_plan_meal_ids)),
                                            method='get',
                                            headers=headers,
                                        )
                                        
                                        if fetch_resp.status_code == 200:
                                            instructions_data = fetch_resp.json()
                                            st.session_state['instructions'] = instructions_data.get('instructions', [])
                                            st.session_state['meal_prep_preference'] = instructions_data.get('meal_prep_preference', 'daily')
                                            
                                            if st.session_state['instructions']:
                                                st.success("✅ Cooking instructions generated successfully!")
                                                
                                                # Trigger gamification event
                                                trigger_gamification_event('cooking_instructions_generated', {
                                                    'meal_plan_id': meal_plan_id,
                                                    'meal_count': len(meal_plan_meal_ids)
                                                })
                                                
                                                st.session_state.active_section = 'cooking_instructions'
                                                st.rerun()  # Refresh to show instructions
                                            else:
                                                st.info("Instructions are being generated. Please check back in a moment.")
                                        else:
                                            st.warning("Instructions are still being generated. Please try viewing them later.")
                                    else:
                                        error_data = gen_resp.json()
                                        st.error(f"Failed to generate instructions: {error_data.get('error', 'Unknown error')}")
                                        
                                except Exception as e:
                                    st.error(f"Error generating cooking instructions: {str(e)}")
                                    logging.error(f"Error generating instructions: {str(e)}")
                                    logging.error(traceback.format_exc())

                with action_cols[1]:
                    if st.button("📝 Edit Selected Meals", use_container_width=True, disabled=is_past_week or selected_data_full.empty):
                        if selected_data_full.empty:
                            st.warning("Please select meals to edit")
                        else:
                            st.session_state.active_section = 'edit_form'
                            st.rerun()

                with action_cols[2]:
                    if st.button("✅ Approve Meal Plan", use_container_width=True, disabled=is_past_week or is_approved):
                        if is_approved:
                            st.info("This meal plan is already approved.")
                        else:
                            st.session_state.active_section = 'approval_options'
                            st.rerun()
                
                # Delete button below the main action buttons
                if st.button("🗑️ Delete Selected Meals", use_container_width=True, disabled=is_past_week or selected_data_full.empty):
                    if selected_data_full.empty:
                        st.warning("Please select meals to delete")
                    else:
                        st.session_state.active_section = 'delete_confirmation'
                        st.rerun()
                
                # Only show the tabbed UI if no other section is active
                # Determine the default tab based on action
                tab_names = ["📊 Overview", "⭐ Reviews", "📝 Meal Reviews"]
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
        st.stop()  # Stop instead of return
    else:
        pass

    # Add a footer
    st.markdown("---")
    st.markdown("### Support SautAI")
    st.markdown("If you enjoy using SautAI, please consider [supporting us](https://ko-fi.com/sautai)")

