import streamlit as st
import pandas as pd
import json # Import json library
from utils import (
    api_call_with_refresh, login_form, toggle_chef_mode, 
    start_or_continue_streaming, client, openai_headers, guest_chat_with_gpt, 
    chat_with_gpt, is_user_authenticated, resend_activation_link, footer,
    get_chef_meals_by_postal_code, replace_meal_with_chef_meal
)
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import requests
import traceback
import time
import re

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

@st.fragment
def generate_meal_plan(selected_week_start, selected_week_end, headers):
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

def fetch_gamification_data():
    """Fetch gamification data from Django backend."""
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/gamification/api/streamlit-data/", 
            method='get',
            headers=headers,
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
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/gamification/api/event/", 
            method='post',
            headers=headers,
            data=payload
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
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/user-profile/",
                method='get',
                headers=headers
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
                   meal_plan_id_from_url=None, meal_id_from_url=None, action=None, selected_tab=None,
                   selected_day=None, selected_week_start=None, day_offset=None):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    current_meal_prep_pref = st.session_state.get('meal_prep_preference', 'daily')

    # Handle payment tab if selected
    if selected_tab == "💳 Payment":
        # Clear payment transition flag since we're now showing the payment UI
        if 'payment_transition_in_progress' in st.session_state:
            del st.session_state['payment_transition_in_progress']
            
        st.markdown("### 💳 Payment for Chef Meals")
        st.info("Your meal plan contains chef-prepared meals that require payment.")

        # Fetch pending order ID from the meal plan details
        pending_order_id = None
        meal_plan_details_resp = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/meal_plans/{meal_plan_id}/",
            method='get',
            headers=headers
        )
        if meal_plan_details_resp.status_code == 200:
            meal_plan_details = meal_plan_details_resp.json()
            pending_order_id = meal_plan_details.get('pending_order_id')
        
        if pending_order_id:
            st.write(f"**Order ID:** {pending_order_id}")
            
            # TODO: Ensure the price stays the same and doesn't show the price difference as orders come in. the refunds will happen after all orders are in.
            # Fetch order details to display
            order_details_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/{pending_order_id}/",
                method='get',
                headers=headers
            )
            
            if order_details_resp and order_details_resp.status_code == 200:
                order_details = order_details_resp.json()

                
                # Display order summary in a clean card
                st.markdown("### Order Summary")
                
                # Create columns for better layout
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Order Information**")
                    st.markdown(f"**Order ID:** {order_details['id']}")
                    st.markdown(f"**Order Date:** {order_details['order_date'].split('T')[0]}")
                    st.markdown(f"**Status:** {order_details['status']}")
                    st.markdown(f"**Delivery Method:** {order_details['delivery_method']}")
                    if order_details.get('special_requests'):
                        st.markdown(f"**Special Requests:** {order_details['special_requests']}")
                
                with col2:
                    st.markdown("**Customer Details**")
                    customer = order_details.get('customer_details', {})
                    st.markdown(f"**Name:** {customer.get('name', 'N/A')}")
                    st.markdown(f"**Email:** {customer.get('email', 'N/A')}")
                    
                    st.markdown("**Payment Information**")
                    st.markdown(f"**Total Price:** ${float(order_details['total_price']):.2f}")
                    payment_status = "Paid" if order_details.get('is_paid') else "Unpaid"
                    st.markdown(f"**Payment Status:** {payment_status}")
                
                # Display order items if available
                if order_details.get('price_breakdown') and len(order_details['price_breakdown']) > 0:
                    st.markdown("### Order Items")
                    
                    # Create a table of items
                    items_data = []
                    
                    for item in order_details['price_breakdown']:
                        # These values already include quantity calculations
                        items_data.append({
                            "Meal": item.get('meal_name', 'Unknown Meal'),
                            "Quantity": item.get('quantity', 1),
                            "Unit Price": f"${float(item.get('unit_price', 0)):.2f}",
                            "Subtotal": f"${float(item.get('subtotal', 0)):.2f}"
                        })
                    
                    if items_data:
                        st.table(items_data)
                        
                        # Use the total_price directly from the API
                        st.markdown(f"**Total Price: ${float(order_details.get('total_price', 0)):.2f}**")
                else:
                    # Fall back to chef_meal_orders if price_breakdown is not available
                    if order_details.get('chef_meal_orders') and len(order_details['chef_meal_orders']) > 0:
                        st.markdown("### Order Items")
                        
                        # Create a table of items
                        items_data = []
                        running_total = 0  # Initialize a running total
                        
                        for meal_order in order_details['chef_meal_orders']:
                            # Calculate the subtotal (unit_price * quantity)
                            unit_price = float(meal_order.get('unit_price', 0))
                            quantity = int(meal_order.get('quantity', 1))
                            subtotal = unit_price * quantity
                            running_total += subtotal  # Add to running total
                            
                            items_data.append({
                                "Meal": meal_order.get('meal_event_details', {}).get('meal_name', 'Unknown Meal'),
                                "Quantity": quantity,
                                "Unit Price": f"${unit_price:.2f}",
                                "Subtotal": f"${subtotal:.2f}"
                            })
                        
                        if items_data:
                            st.table(items_data)
                            st.markdown(f"**Total Price: ${float(order_details.get('total_price', 0)):.2f}**")
                    else:
                        st.info("No meal items found in this order.")
                    
                # Add payment action button if unpaid
                if not order_details.get('is_paid'):
                    st.markdown("### Complete Your Order")
                    if st.button("Proceed to Payment"):
                        st.session_state.payment_order_id = order_details['id']
                        st.rerun()  # Redirect to payment flow
            
            # Show payment options in columns
            payment_cols = st.columns(3)
            
            # Column 1: Proceed to Payment
            with payment_cols[0]:
                if st.button("💳 Proceed to Payment", type="primary", use_container_width=True):
                    with st.spinner("Initiating secure payment..."):
                        try:
                            payment_resp = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/meals/api/process-chef-meal-payment/{pending_order_id}/",
                                method='post',
                                headers=headers,
                                data={}
                            )
                            if not payment_resp:
                                st.error("❌ Payment initiation failed: Checkout URL not received from the server.")
                            elif payment_resp.status_code == 200:
                                payment_data = payment_resp.json()
                                session_url = payment_data.get('session_url')
                                if session_url:
                                    # Store the *latest* URL in case needed
                                    st.session_state[f'payment_url_{pending_order_id}'] = session_url
                                    st.success("✅ Payment session created!")
                                    st.markdown("Click the link below to complete payment:")
                                    st.link_button("Go to Checkout", session_url, use_container_width=True)
                                    st.info("You may need to refresh after payment.")
                                else:
                                    # Provide specific error when URL is missing
                                    st.error("❌ Payment initiation failed: Checkout URL not received from the server.")
                            elif payment_resp.status_code == 402:
                                # Handle already paid or not required
                                error_data = payment_resp.json()
                                st.warning(f"⚠️ {error_data.get('message', 'Payment cannot be processed.')}") # More prominent warning
                            else:
                                # Handle other errors with more detail
                                error_msg = f"Failed to initiate payment (Status: {payment_resp.status_code})."
                                if payment_resp.text:
                                    try:
                                        error_data = payment_resp.json()
                                        error_msg += f" Server message: {error_data.get('message', 'No additional details provided.')}"
                                    except json.JSONDecodeError:
                                        error_msg += f" Server response: {payment_resp.text}"
                                st.error(f"❌ {error_msg}") # More prominent error
                        except Exception as e:
                            st.error(f"❌ An error occurred during payment initiation: {str(e)}") # More prominent error
                            logging.error(f"Payment initiation error: {str(e)}", exc_info=True)
                            
            # Column 2: Resend Payment Link Email
            with payment_cols[1]:
                if st.button("✉️ Send Payment Link Email", use_container_width=True):
                    with st.spinner("Sending payment link email..."):
                        try:
                            resend_resp = api_call_with_refresh(
                                url=f"{os.getenv('DJANGO_URL')}/meals/api/resend-payment-link/{pending_order_id}/",
                                method='post',
                                headers=headers,
                                data={}
                            )
                            if resend_resp.status_code == 200:
                                st.success("✅ Payment link resent! Please check your email.")
                            else:
                                error_msg = "Failed to resend payment link."
                                if resend_resp.text:
                                    try:
                                        error_data = resend_resp.json()
                                        error_msg = error_data.get('message', error_msg)
                                    except json.JSONDecodeError:
                                        error_msg += f" Server response: {resend_resp.text}"
                                st.error(error_msg)
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
                            logging.error(f"Resend link error: {str(e)}", exc_info=True)
                            
            # Column 3: Go Back to Overview
            with payment_cols[3-1]:
                if st.button("⬅️ Back to Overview", use_container_width=True):
                    # Instead of directly setting selected_tab, set a flag that will be checked
                    # before the radio button widget is created
                    st.session_state['switch_to_overview'] = True
                    st.rerun()
            
            # Display existing link if already generated
            existing_payment_url = st.session_state.get(f'payment_url_{pending_order_id}')
            if existing_payment_url:
                st.markdown("Use this link to complete payment:")
                st.link_button("Go to Checkout", existing_payment_url, use_container_width=True)
        else:
            st.error("Missing order information for payment. Please refresh or contact support.")
            
        # Display a collapsible section with more information about chef meals
        with st.expander("About Chef Meals"):
            st.markdown("""
            ### 👨‍🍳 Chef-Prepared Meals
            
            Chef meals are specially prepared by professional chefs in your area. Unlike 
            AI-generated meal suggestions, these meals:
            
            - Are made by real local chefs
            - Use fresh, locally-sourced ingredients
            - Are delivered ready to heat and eat
            - Support local culinary businesses
            
            **Payment is required to confirm your order with the chef.**
            """)
            
    # This function now only shows tab-specific content, not the main actions
    elif selected_tab == "📊 Overview":
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

    elif selected_tab == "👨‍🍳 Chef Meals":
        st.write("### 👨‍🍳 Chef-Created Meals in Your Area")
        
        # Add an introduction to chef meals feature
        with st.expander("About Chef Meals", expanded=True):
            st.markdown("""
            **Chef-created meals are prepared by professional chefs in your area and delivered to your door.**
            
            - Browse meals created by local chefs available for delivery to your postal code
            - Filter by meal type, date, and dietary compatibility
            - Replace any meal in your plan with a chef-created alternative
            - Support local culinary talent while enjoying delicious, ready-made meals
            
            *Note: Chef meals may have additional costs and delivery fees.*
            """)
        
        # Initialize session state variables for chef meals tab if they don't exist
        if 'chef_meal_type_filter' not in st.session_state:
            st.session_state.chef_meal_type_filter = None
        if 'chef_compatible_only' not in st.session_state:
            st.session_state.chef_compatible_only = False
        if 'chef_meals_page' not in st.session_state:
            st.session_state.chef_meals_page = 1
        if 'chef_selected_day' not in st.session_state:
            st.session_state.chef_selected_day = "All Days"
            
        # Add explanation for the filters
        st.markdown("""
        Filter chef-created meals to find options that meet your needs. Chef meals are only available on specific dates 
        and must be ordered in advance.
        """)
            
        # Create filter controls
        filter_cols = st.columns([1, 1, 1, 1])
        
        with filter_cols[0]:
            meal_type_options = ["All Types", "Breakfast", "Lunch", "Dinner"]
            selected_meal_type = st.selectbox(
                "Meal Type",
                options=meal_type_options,
                index=0,
                key="chef_meal_type_selector"
            )
            st.session_state.chef_meal_type_filter = None if selected_meal_type == "All Types" else selected_meal_type
            
        with filter_cols[1]:
            # Show days of the week for the selected week instead of a date picker
            days_of_week = ["All Days"] + [
                (selected_week_start + timedelta(days=i)).strftime("%A (%b %d)")
                for i in range(7)
            ]
            
            # Default to the selected day from the meal plan view if it exists
            default_index = 0
            if selected_day != "All Days":
                for i, day_str in enumerate(days_of_week):
                    if day_str.startswith(selected_day):
                        default_index = i
                        break
            
            chef_selected_day = st.selectbox(
                "Day",
                options=days_of_week,
                index=default_index,
                key="chef_day_selector"
            )
            st.session_state.chef_selected_day = chef_selected_day
            
        with filter_cols[2]:
            compatible_only = st.toggle(
                "Show Compatible Meals Only",
                value=st.session_state.chef_compatible_only,
                key="chef_meal_compatibility_toggle"
            )
            st.session_state.chef_compatible_only = compatible_only
            
        with filter_cols[3]:
            if st.button("🔄 Refresh Chef Meals", use_container_width=True):
                st.session_state.chef_meals_page = 1  # Reset to first page when refreshing
                st.rerun()
        
        # Extract date from the selected day if needed
        selected_date = None
        if chef_selected_day != "All Days":
            day_name = chef_selected_day.split(" ")[0]
            if day_name in day_offset:
                selected_date = (selected_week_start + timedelta(days=day_offset[day_name])).strftime('%Y-%m-%d')
        
        # Fetch chef meals by postal code using the get_chef_meals_by_postal_code function
        chef_meals_data = get_chef_meals_by_postal_code(
            meal_type=st.session_state.chef_meal_type_filter,
            date=selected_date,  # Only use date if a specific day is selected
            week_start_date=selected_week_start.strftime('%Y-%m-%d') if not selected_date else None,
            chef_id=st.session_state.chef_id_filter if 'chef_id_filter' in st.session_state else None,
            include_compatible_only=st.session_state.chef_compatible_only,
            page=st.session_state.chef_meals_page
        )
        
        if chef_meals_data:
            meals = chef_meals_data.get('data', {}).get('meals', [])

            if meals:
                # Filter meals by day if specific day selected
                if chef_selected_day != "All Days" and selected_date:
                    filtered_meals = []
                    for meal in meals:
                        available_dates = meal.get('available_dates', {})
                        if selected_date in available_dates:
                            # Add day-specific information
                            meal['event_info'] = available_dates[selected_date]
                            filtered_meals.append(meal)
                    meals = filtered_meals
                
                if meals:  # Check again after filtering
                    st.success(f"Found {len(meals)} chef meals available for the selected filters!")
                    
                    # Show meals in a grid layout
                    meal_container = st.container()
                    
                    # Show 3 meals per row
                    meals_per_row = 3
                    for i in range(0, len(meals), meals_per_row):
                        row_meals = meals[i:i+meals_per_row]
                        cols = meal_container.columns(len(row_meals))
                        
                        for idx, meal in enumerate(row_meals):
                            with cols[idx]:
                                # Create a card-like layout for each meal
                                is_compatible = meal.get('is_compatible', False)
                                
                                # Add compatibility badge/indicator
                                compatibility_badge = "✅ Compatible" if is_compatible else "⚠️ May not match preferences"
                                compatibility_color = "green" if is_compatible else "orange"
                                
                                # Get meal events for this meal
                                event_info = meal.get('event_info', {})
                                available_dates = meal.get('available_dates', {})
                                available_days_count = meal.get('available_days_count', 0)
                                
                                # Get rating information
                                rating = meal.get('average_rating', 0)
                                # Handle case where rating might be None
                                if rating is None:
                                    rating = 0
                                rating_stars = "⭐" * int(rating) + ("½" if rating % 1 >= 0.5 else "")
                                
                                # Create meal card with improved styling
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; border-radius:10px; padding:15px; height:100%; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                    <h4>{meal.get('name', 'Unnamed Meal')}</h4>
                                    <p><strong>Chef:</strong> {meal.get('chef_name', 'Unknown Chef')}</p>
                                    <p><strong>Type:</strong> {meal.get('meal_type', 'Unknown Type')}</p>
                                    <p><strong>Price:</strong> ${float(meal.get('chef_meal_events', [{}])[0].get('current_price', meal.get('price', 0))):.2f}</p>
                                    <p><strong>Rating:</strong> {rating_stars if rating > 0 else 'No ratings yet'}</p>
                                    <p><span style="color:{compatibility_color}; font-weight:bold;">{compatibility_badge}</span></p>
                                """, unsafe_allow_html=True)
                                
                                # Display availability information
                                if chef_selected_day == "All Days":
                                    st.markdown(f"<p><strong>Available on:</strong> {available_days_count} day{'s' if available_days_count != 1 else ''} this week</p>", unsafe_allow_html=True)
                                    
                                    # Show the available days
                                    if available_dates:
                                        days_str = ", ".join([f"{info['day_name']}" for date, info in available_dates.items()])
                                        st.markdown(f"<p><small>Available days: {days_str}</small></p>", unsafe_allow_html=True)
                                elif event_info:
                                    # Show detailed information for the selected day
                                    event_time = event_info.get('event_time', '')
                                    orders_count = event_info.get('orders_count', 0)
                                    max_orders = event_info.get('max_orders', 0)
                                    day_name = event_info.get('day_name', '')
                                    
                                    st.markdown(f"<p><strong>Delivery:</strong> {day_name} at {event_time}</p>", unsafe_allow_html=True)
                                    
                                    if max_orders > 0:
                                        capacity = int((orders_count / max_orders) * 100)
                                        capacity_color = "green" if capacity < 50 else ("orange" if capacity < 80 else "red")
                                        st.markdown(f"<p><span style='color:{capacity_color};'><strong>Capacity:</strong> {capacity}% full ({orders_count}/{max_orders} orders)</span></p>", unsafe_allow_html=True)
                                    
                                    # Display the event-specific price if available
                                    if 'price' in event_info:
                                        event_price = event_info.get('price')
                                        st.markdown(f"<p><strong>Event Price:</strong> ${float(event_price):.2f}</p>", unsafe_allow_html=True)
                                    # Or display the price from chef_meal_events if available
                                    elif meal.get('chef_meal_events'):
                                        for event in meal.get('chef_meal_events', []):
                                            if event.get('id') == event_info.get('event_id'):
                                                event_price = event.get('current_price')
                                                if event_price is not None:
                                                    st.markdown(f"<p><strong>Event Price:</strong> ${float(event_price):.2f}</p>", unsafe_allow_html=True)
                                                break
                                
                                # Display description
                                st.markdown(f"<p><small>{meal.get('description', '')[:100]}{'...' if len(meal.get('description', '')) > 100 else ''}</small></p>", unsafe_allow_html=True)
                                
                                # Display dietary preferences if available
                                dietary_prefs = meal.get('dietary_preferences', [])
                                if dietary_prefs:
                                    pref_list = ", ".join(dietary_prefs[:3])
                                    if len(dietary_prefs) > 3:
                                        pref_list += f" +{len(dietary_prefs)-3} more"
                                    st.markdown(f"<p><strong>Dietary:</strong> {pref_list}</p>", unsafe_allow_html=True)
                                
                                # Close the div
                                st.markdown("</div>", unsafe_allow_html=True)
                                
                                # Add a button to replace a meal with this chef meal
                                if st.button(f"🔄 Replace with this Meal", key=f"replace_btn_{meal.get('id')}", use_container_width=True):
                                    # Show replacement options - only show meals of the same type
                                    meal_type = meal.get('meal_type')
                                    replacement_options = meal_plan_df[meal_plan_df['Meal Type'] == meal_type]
                                    
                                    # If a specific day is selected, prefer meals from that day
                                    if chef_selected_day != "All Days":
                                        day_name = chef_selected_day.split(" ")[0]
                                        day_filtered_options = replacement_options[replacement_options['Day'] == day_name]
                                        if not day_filtered_options.empty:
                                            replacement_options = day_filtered_options
                                    
                                    if replacement_options.empty:
                                        st.warning(f"No {meal_type.lower()} meals in your plan to replace.")
                                    else:
                                        st.session_state[f'replacing_with_chef_meal_{meal.get("id")}'] = True
                                        st.session_state[f'chef_meal_to_replace_{meal.get("id")}'] = meal
                                        st.rerun()
                                
                                # Show replacement selection if this meal is being used for replacement
                                if st.session_state.get(f'replacing_with_chef_meal_{meal.get("id")}', False):
                                    chef_meal = st.session_state.get(f'chef_meal_to_replace_{meal.get("id")}')
                                    meal_type = chef_meal.get('meal_type')
                                    
                                    st.subheader(f"Select a {meal_type} to replace:")
                                    
                                    # Get available dates for this chef meal
                                    available_dates = chef_meal.get('available_dates', {})
                                    
                                    # Filter replacement options by meal type AND date
                                    replacement_options = meal_plan_df[meal_plan_df['Meal Type'] == meal_type]
                                    
                                    # Further filter by matching the date
                                    valid_replacement_options = []
                                    replacement_meals = []
                                    
                                    for _, row in replacement_options.iterrows():
                                        meal_date = row['Meal Date']
                                        meal_day = row['Day']
                                        date_str = meal_date.strftime('%Y-%m-%d')
                                        
                                        # Check if this meal's date is in the chef meal's available dates
                                        if date_str in available_dates:
                                            valid_replacement_options.append(row)
                                            replacement_meals.append(f"{row['Meal Name']} ({meal_day} - {meal_date.strftime('%b %d')})")
                                    
                                    if not replacement_meals:
                                        st.warning(f"No {meal_type} meals found that match the chef meal's available dates.")
                                        st.info("Chef meals can only replace meals on the same date as the chef meal's scheduled event.")
                                        
                                        if st.button("Cancel", key=f"no_matches_cancel_{meal.get('id')}"):
                                            del st.session_state[f'replacing_with_chef_meal_{meal.get("id")}']
                                            del st.session_state[f'chef_meal_to_replace_{meal.get("id")}']
                                            st.rerun()
                                    else:
                                        selected_replacement = st.selectbox(
                                            f"Choose meal to replace with {chef_meal.get('name')}",
                                            options=replacement_meals,
                                            key=f"replacement_select_{meal.get('id')}"
                                        )
                                    
                                    # Extract meal name without the day part
                                    selected_meal_name = selected_replacement.split(" (")[0]
                                    day_date_info = selected_replacement.split("(")[1].split(")")[0]
                                    selected_day = day_date_info.split(" - ")[0]
                                    
                                    # Use the filtered valid options instead of all replacement options
                                    selected_row = pd.DataFrame(valid_replacement_options)[
                                        (pd.DataFrame(valid_replacement_options)['Meal Name'] == selected_meal_name) & 
                                        (pd.DataFrame(valid_replacement_options)['Day'] == selected_day)
                                    ]
                                    
                                    if not selected_row.empty:
                                        selected_meal_plan_meal_id = selected_row['Meal Plan Meal ID'].values[0]
                                        
                                        # Get event ID for the selected day if available
                                        event_id = None
                                        available_dates = chef_meal.get('available_dates', {})

                                        # Find the date for the selected day
                                        if selected_day in day_offset:
                                            selected_date = (selected_week_start + timedelta(days=day_offset[selected_day])).strftime('%Y-%m-%d')
                                            if selected_date in available_dates:
                                                event_id = available_dates[selected_date].get('event_id')
                                        
                                        if not event_id:
                                            st.warning("Could not find a valid event for this date. Please try another meal.")
                                            
                                        # Add quantity selection and special requests before confirming
                                        meal_price = float(chef_meal.get('chef_meal_events', [{}])[0].get('current_price', chef_meal.get('price', 0)))
                                        
                                        # Display quantity selector
                                        st.markdown("### How many meals would you like to order?")
                                        st.markdown("*(Ideal for families or meal prep)*")
                                        
                                        quantity = st.number_input(
                                            "Quantity", 
                                            min_value=1, 
                                            max_value=10, 
                                            value=1, 
                                            step=1,
                                            key=f"quantity_input_{meal.get('id')}"
                                        )
                                        
                                        # Display total price
                                        total_price = meal_price * quantity
                                        st.markdown(f"**Total Price:** ${total_price:.2f} (${meal_price:.2f} x {quantity})")
                                        
                                        # Special requests
                                        special_requests = st.text_area(
                                            "Special Requests (Optional)", 
                                            placeholder="Any dietary restrictions, allergies, or preparation preferences?",
                                            key=f"special_requests_{meal.get('id')}"
                                        )
                                            
                                        confirm_col1, confirm_col2 = st.columns(2)
                                        with confirm_col1:
                                            if st.button("Confirm Replacement", key=f"confirm_replace_{meal.get('id')}", type="primary"):
                                                # Call API to replace the meal
                                                with st.spinner("Replacing meal..."):
                                                    replace_result = replace_meal_with_chef_meal(
                                                        meal_plan_meal_id=selected_meal_plan_meal_id,
                                                        chef_meal_id=meal.get('id'),
                                                        event_id=event_id,
                                                        quantity=quantity,
                                                        special_requests=special_requests
                                                    )
                                                    
                                                    if replace_result:
                                                        st.success(f"Successfully replaced {selected_meal_name} with {quantity} {chef_meal.get('name')} meal{'s' if quantity > 1 else ''}!")
                                                        
                                                        # Trigger gamification event for replacing with chef meal
                                                        trigger_gamification_event('replaced_with_chef_meal', {
                                                            'meal_plan_id': meal_plan_id,
                                                            'chef_meal_id': meal.get('id')
                                                        })
                                                        
                                                        # Clear replacement state and refresh page
                                                        del st.session_state[f'replacing_with_chef_meal_{meal.get("id")}']
                                                        del st.session_state[f'chef_meal_to_replace_{meal.get("id")}']
                                                        time.sleep(1)  # Give time to read the success message
                                                        st.rerun()
                                                    else:
                                                        st.error("Failed to replace meal. Please try again.")
                                                        
                                        with confirm_col2:
                                            if st.button("Cancel", key=f"cancel_replace_{meal.get('id')}"):
                                                del st.session_state[f'replacing_with_chef_meal_{meal.get("id")}']
                                                del st.session_state[f'chef_meal_to_replace_{meal.get("id")}']
                                                st.rerun()
                    
                    # Add pagination controls
                    st.markdown("---")
                    total_pages = chef_meals_data.get('data', {}).get('total_pages', 1)
                    current_page = chef_meals_data.get('data', {}).get('current_page', 1)
                    
                    pagination_cols = st.columns([1, 3, 1])
                    with pagination_cols[0]:
                        if current_page > 1:
                            if st.button("◀️ Previous Page", use_container_width=True):
                                st.session_state.chef_meals_page -= 1
                                st.rerun()
                    with pagination_cols[1]:
                        st.markdown(f"<h4 style='text-align: center;'>Page {current_page} of {total_pages}</h4>", unsafe_allow_html=True)
                    with pagination_cols[2]:
                        if current_page < total_pages:
                            if st.button("Next Page ▶️", use_container_width=True):
                                st.session_state.chef_meals_page += 1
                                st.rerun()
                else:
                    day_message = f" for {chef_selected_day}" if chef_selected_day != "All Days" else ""
                    st.warning(f"No chef meals available{day_message} with the selected filters.")
                    st.markdown("""
                    Try adjusting your filters:
                    - Select "All Days" to see meals available on any day
                    - Try a different meal type
                    - Uncheck "Compatible Meals Only" to see all options
                    """)
                            
            else:
                chef_postal_code = st.session_state.get('address', {}).get('postalcode', 'your area')
                st.info(f"No chef meals available in {chef_postal_code} for the selected filters.")
                
                # Add helpful information in a visually appealing layout
                st.markdown("""
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                    <h4>💡 Tips for Finding Chef Meals</h4>
                    <ul>
                        <li><strong>Try different days</strong> - Chef meals are often scheduled for specific days</li>
                        <li><strong>Adjust meal type filters</strong> - Try looking for breakfast, lunch, or dinner options</li>
                        <li><strong>Check compatibility settings</strong> - Uncheck "Compatible Meals Only" to see all options</li>
                        <li><strong>Check back regularly</strong> - New chef meals are added throughout the week</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Add a button to sign up for notifications
                notification_cols = st.columns(2)
                with notification_cols[0]:
                    if st.button("Notify Me When Chef Meals Become Available", use_container_width=True):
                        with st.spinner("Setting up notifications..."):
                            # Here you would integrate with your notification system
                            # For now, just show a success message
                            time.sleep(1)
                            st.success("You'll be notified when new chef meals are available in your area!")
                with notification_cols[1]:
                    if st.button("See Featured Recipes Instead", use_container_width=True):
                        # Switch to the meal plans tab
                        st.session_state.active_section = None
                        # Set the tab to Overview
                        st.session_state._radio_key = tab_names[0]
                        st.rerun()
        else:
            # Check if postal code is missing
            if 'address' not in st.session_state or not st.session_state.get('address', {}).get('postalcode'):
                st.warning("Please set your postal code in your profile to see available chef meals.")
                if st.button("Go to Profile Settings"):
                    st.switch_page("views/5_account.py")
            else:
                st.error("No chef meal data available at this time.")
                st.markdown("""
                **Possible reasons:**
                - Chef meal service may not be active in your area yet
                - There may be a temporary service disruption
                - No chefs are currently offering meals in your postal code area
                
                Please check back later or contact support if this issue persists.
                """)
                
                # Add a prompt for users to check back later
                st.info("Chef meal availability varies by location and is continuously expanding. We're adding new chefs and areas regularly!")
                
                # Add a button to navigate back to regular meal plans
                if st.button("View Regular Meal Plan Instead", use_container_width=True):
                    # Switch to the meal plans tab
                    st.session_state.active_section = None
                    # Set the tab to Overview
                    st.rerun()

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
        login_form()
    with login_cols[1]:
        if st.button("Create Account", use_container_width=True):
            st.switch_page("views/7_register.py")
            
    
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
                generate_meal_plan(selected_week_start, selected_week_end, headers)

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
        days_of_week = [(selected_week_start + timedelta(days=i)).strftime('%a') for i in range(7)] # Use %a for abbreviated day name
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
        if not response:
            st.error("❌ Error fetching meal plans: Checkout URL not received from the server.")
            st.stop()
        if response.status_code == 200:
            meal_plan_data = response.json()
            
            # Extract meal_plans list if we have a dictionary with meal_plans key
            if isinstance(meal_plan_data, dict) and 'meal_plans' in meal_plan_data:
                meal_plans_list = meal_plan_data['meal_plans']
                
                if not meal_plans_list:
                    st.info("No meals found for this week.")
                    st.stop()
                
                # Now we can access the first meal plan in the list
                meal_plan = meal_plans_list[0]
            
            # Handle the original expected format as fallback
            elif isinstance(meal_plan_data, list):
                if not meal_plan_data:
                    st.info("No meals found for this week.")
                    st.stop()
                
                meal_plan = meal_plan_data[0]
            
            # Add other error cases after the most likely cases
            elif isinstance(meal_plan_data, dict) and 'results' in meal_plan_data:
                results = meal_plan_data['results']
                if isinstance(results, list) and len(results) > 0:
                    meal_plan = results[0]
                else:
                    st.info("No meals found for this week.")
                    st.stop()
            else:
                st.info("No meals found for this week. Unexpected data format received.")
                st.stop()

            # Continue with the rest of the code
            try:
                meal_plan_id = meal_plan['id']
                st.session_state['meal_prep_preference'] = meal_plan['meal_prep_preference']
            except Exception as e:
                st.error("Error processing meal plan data: invalid structure.")
                st.stop()

            meal_plan_details_resp = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/meal_plans/{meal_plan_id}/",
                method='get',
                headers=headers
            )

            is_approved = False
            pending_order_id_from_api = None # Initialize
            if meal_plan_details_resp.status_code == 200:
                meal_plan_details = meal_plan_details_resp.json()
                # print(f"Meal plan details: {meal_plan_details}")
                is_approved = meal_plan_details.get('is_approved', False)
                
                # --- Check for pending payment based on API response --- #
                payment_required_from_api = meal_plan_details.get('payment_required', False)
                pending_order_id_from_api = meal_plan_details.get('pending_order_id')
                
                # Store pending order ID if payment is required
                if payment_required_from_api and pending_order_id_from_api:
                    st.session_state['pending_chef_order_id'] = pending_order_id_from_api
                elif 'pending_chef_order_id' in st.session_state:
                    # Clear if payment no longer required or no pending order
                    del st.session_state['pending_chef_order_id']
                # --- End Check --- #

            meal_plan_records = []
            day_offset = { 'Monday':0,'Tuesday':1,'Wednesday':2,'Thursday':3,'Friday':4,'Saturday':5,'Sunday':6 }

            for m in meal_plan['meals']:
                meal_day = m['day']
                meal_plan_meal_id = m['meal_plan_meal_id']
                meal_date = selected_week_start + timedelta(days=day_offset[meal_day])
                
                # Check if this is a chef meal - correctly use is_chef_meal instead of chef_meal
                is_chef_meal = m.get('is_chef_meal', False)
                
                # As a fallback, also check in the meal object if the top-level flag isn't present
                if not is_chef_meal and 'meal' in m and isinstance(m['meal'], dict):
                    is_chef_meal = m['meal'].get('is_chef_meal', False)
                
                # For additional verification, we could also check if chef_name is not None
                if not is_chef_meal and m.get('chef_name') is not None:
                    is_chef_meal = True
                
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
                    'is_chef_meal': is_chef_meal,  # Add flag for chef meals
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
                ),
                "is_chef_meal": st.column_config.Column(
                    "Source",
                    help="Meal source: Chef-created or AI-generated",
                    width="small"
                )
            }

            # Keep Meal Plan Meal ID in the display DataFrame but hide it from view
            display_df = meal_plan_df.drop(columns=['Meal Plan ID', 'meal_id'])
            
            # Format the is_chef_meal column to show as a badge with different colors
            if 'is_chef_meal' in display_df.columns:
                def format_source_badge(is_chef):
                    if is_chef:
                        # More distinctive badge for chef meals
                        return "👨‍🍳 CHEF"
                    else:
                        # More distinctive badge for AI meals
                        return "🤖 ASSISTANT"
                
                display_df['is_chef_meal'] = display_df['is_chef_meal'].apply(format_source_badge)
                
                # Rename the column to "Source" for better clarity
                display_df = display_df.rename(columns={'is_chef_meal': 'Source'})
                
                # Also modify the meal name to include visual indication
                display_df['Meal Name'] = display_df.apply(
                    lambda row: f"⭐ {row['Meal Name']} ⭐" if row['Source'].startswith('👨‍🍳') else row['Meal Name'],
                    axis=1
                )
            
            display_df = display_df[['Select', 'Day', 'Meal Type', 'Meal Name', 'Description', 'Meal Date', 'Source' if 'Source' in display_df.columns else 'is_chef_meal', 'Meal Plan Meal ID']]

            # Add meal type icons
            meal_type_icons = {
                'Breakfast': '🍳',
                'Lunch': '🥗',
                'Dinner': '🍽️'
            }
            display_df['Meal Type'] = display_df['Meal Type'].apply(lambda x: f"{meal_type_icons.get(x, '')} {x}")
            
            # Remove the previous styling code that doesn't work with data_editor
            # Configure the Meal Plan Meal ID column to be disabled (read-only)
            column_config["Meal Plan Meal ID"] = st.column_config.Column(
                "Meal Plan Meal ID",
                help="Internal ID",
                width="small",
                disabled=True
            )
            
            # Update column config for Source
            if 'Source' in display_df.columns:
                # Add chef information to the DataFrame for use in tooltips
                chef_info = {}
                for m in meal_plan['meals']:
                    if m.get('is_chef_meal') and m.get('chef_name'):
                        meal_plan_meal_id = m['meal_plan_meal_id']
                        # Check first for chef_meal_events pricing
                        if 'chef_meal_events' in m['meal'] and m['meal']['chef_meal_events']:
                            price = m['meal']['chef_meal_events'][0].get('current_price', 
                                  m['meal'].get('current_price', 
                                  m['meal'].get('price', 'Price not available')))
                        else:
                            price = m['meal'].get('current_price', 
                                  m['meal'].get('price', 'Price not available'))
                            
                        chef_info[meal_plan_meal_id] = {
                            'chef_name': m.get('chef_name', 'Unknown Chef'),
                            'price': price
                        }
                
                # Create help text with chef information when available
                def get_source_help_text(row):
                    if row['Source'].startswith('👨‍🍳'):
                        meal_plan_meal_id = row['Meal Plan Meal ID']
                        if meal_plan_meal_id in chef_info:
                            chef_data = chef_info[meal_plan_meal_id]
                            return f"Created by Chef {chef_data['chef_name']} - Price: ${chef_data['price']}"
                    return "Meal source: Chef-created or AI-generated"
                
                # Add the help text column
                if chef_info:
                    display_df['Source_Help'] = display_df.apply(get_source_help_text, axis=1)
                    # Use custom tooltips for each row
                    column_config["Source"] = st.column_config.Column(
                        "Source",
                        help="Hover for details about the meal source",
                        width="medium"
                    )
                else:
                    column_config["Source"] = st.column_config.Column(
                        "Source",
                        help="Meal source: Chef-created or AI-generated",
                        width="medium"
                    )
            elif 'is_chef_meal' in display_df.columns:
                column_config["is_chef_meal"] = st.column_config.Column(
                    "Source",
                    help="Meal source: Chef-created or AI-generated",
                    width="medium"
                )
            
            selected_rows = st.data_editor(
                display_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config=column_config,
                column_order=["Select", "Day", "Meal Type", "Meal Name", 'Source' if 'Source' in display_df.columns else 'is_chef_meal', "Description", "Meal Date"]
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
                                
                                # DEBUG: Print response status and content

                                if approve_resp and approve_resp.status_code == 200:
                                    response_data = approve_resp.json()
                                    message = response_data.get('message', 'Meal plan approved successfully!')
                                    order_id = response_data.get('order_id')
                                    requires_payment = response_data.get('requires_payment', False)

                                    # Clear the pending chef order ID
                                    if 'pending_chef_order_id' in st.session_state:
                                        del st.session_state['pending_chef_order_id']

                                    st.success(message)

                                    # Trigger gamification event
                                    trigger_gamification_event('meal_plan_approved', {
                                        'meal_plan_id': meal_plan_id,
                                        'meal_prep_preference': prep_preference
                                    })

                                    st.balloons()


                                    if order_id and requires_payment:
                                        # DEBUG: Entering payment required block

                                        st.info(f"Payment is required for chef meals in this plan. Order ID: {order_id}")
                                        st.session_state['pending_chef_order_id'] = order_id
                                        # Directly set the tab to payment and rerun
                                        st.session_state['selected_tab'] = "💳 Payment"
                                        # DEBUG: Check active section value
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        # No action needed here regarding flags
                                        pass
                                else:
                                    st.error(f"Error approving meal plan. Status code: {approve_resp.status_code}")
                                    # Attempt to parse and display backend error message
                                    if approve_resp.text:
                                        try:
                                            error_data = approve_resp.json()
                                            st.error(error_data.get('message', f'Approval failed: {approve_resp.text}'))
                                        except json.JSONDecodeError:
                                            st.error(f"Approval failed: {approve_resp.text}")

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

            # ++ Add new section handler for payment ++
            elif st.session_state.active_section == 'payment_required':
                # When payment_required section is active, redirect to the payment tab
                # instead of showing a separate payment UI
                st.session_state.active_section = None  # Clear active section
                st.session_state['selected_tab'] = "💳 Payment"  # Select payment tab
                # REMOVE the flag setting below
                # st.session_state['payment_transition_in_progress'] = True 
                st.rerun()  # Refresh to show the payment tab

            else:
                # Show action buttons only if no other section is active
                action_cols = st.columns(3)
                
                # REMOVE the block below that shows the extra button
                # Check if there's a pending payment to display Pay Now button
                # pending_payment = 'pending_chef_order_id' in st.session_state and st.session_state.get('pending_chef_order_id')
                # 
                # if pending_payment:
                #    # Add a Pay Now button at the top
                #    st.warning("⚠️ You have a pending payment for chef meals in this plan.")
                #    if st.button("💳 Pay Now", type="primary", use_container_width=True):
                #        st.session_state.active_section = 'payment_required'
                #        st.rerun()
                #    
                #    st.markdown("---")  # Add a separator between payment notice and regular actions
                
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

                # Add payment tab if payment is required
                payment_required = meal_plan_details.get('payment_required', False) 
                payment_tab_name = "💳 Payment" # Define for consistency
                
                if payment_required:
                    tab_names = [payment_tab_name, "📊 Overview", "⭐ Reviews", "📝 Meal Reviews", "👨‍🍳 Chef Meals"]
                else:
                    tab_names = ["📊 Overview", "⭐ Reviews", "📝 Meal Reviews", "👨‍🍳 Chef Meals"]

                # Check for the navigation flag before determining the initial tab
                if st.session_state.get('switch_to_overview', False):
                    st.session_state['selected_tab'] = "📊 Overview"
                    # Clear the flag
                    del st.session_state['switch_to_overview']
                # Only set the tab if it's not already set
                elif 'selected_tab' not in st.session_state:
                    # Determine which tab should be selected INITIALLY
                    initial_default_tab_name = tab_names[0] # Default to the first tab
    
                    # If coming from a meal review URL
                    if action == 'review_meal' and meal_plan_id_from_url and meal_id_from_url:
                        review_tab_name = "📝 Meal Reviews"
                        if review_tab_name in tab_names:
                            initial_default_tab_name = review_tab_name
                    # If payment is required and we're not already directed by another action
                    elif payment_required and payment_tab_name in tab_names and initial_default_tab_name != "📝 Meal Reviews":
                         initial_default_tab_name = payment_tab_name
                    
                    st.session_state['selected_tab'] = initial_default_tab_name
                # Ensure the current selected_tab is valid, reset if not (e.g., payment tab removed)
                elif st.session_state['selected_tab'] not in tab_names:
                     st.session_state['selected_tab'] = tab_names[0]


                # Use a radio to simulate tabs, relying on the key for state management
                # The widget will automatically read/write to st.session_state['selected_tab']
                st.radio(
                    "Sections", 
                    tab_names, 
                    key='selected_tab' # Let the widget manage state via this key
                    # No index argument needed anymore
                 )

                # Make sure day_offset is defined and available for the function call
                if 'day_offset' not in locals():
                    day_offset = {'Monday':0,'Tuesday':1,'Wednesday':2,'Thursday':3,'Friday':4,'Saturday':5,'Sunday':6}

                # Pass the current value from session state to the UI function
                show_normal_ui(
                    meal_plan_df, meal_plan_id, is_approved, is_past_week, selected_data_full,
                    meal_plan_id_from_url, meal_id_from_url, action, st.session_state.selected_tab, # Use state value
                    selected_day, selected_week_start, day_offset
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

# Check if we're returning from payment section to ensure visibility of the transition
if st.session_state.get('return_from_payment'):
    st.success("✅ You can pay later when you're ready.")
    # Clear the return flag
    del st.session_state['return_from_payment']
    # Clear payment transition flag if it exists
    if 'payment_transition_in_progress' in st.session_state:
        del st.session_state['payment_transition_in_progress']
    # Rerun to clear the success message after showing it
    time.sleep(1)
    st.rerun()
    
st.markdown("---")  # Add a separator

# Add a footer
st.markdown(
    """
    <a href="https://www.buymeacoffee.com/sautai" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px; width: 217px;" >
    </a>
    """,
    unsafe_allow_html=True
)


    
# Show action buttons only if no other section is active
action_cols = st.columns(3)


