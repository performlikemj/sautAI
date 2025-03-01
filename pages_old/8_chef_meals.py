import streamlit as st
import pandas as pd
import requests
import os
import json
import time
import traceback
import datetime
import logging
from datetime import datetime, timedelta
from utils import api_call_with_refresh, login_form, toggle_chef_mode, is_user_authenticated, validate_input, footer

# Set page config
st.set_page_config(
    page_title="SautAI - Chef Meals",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

# Function to format currency
def format_currency(amount):
    return f"${float(amount):.2f}"

# Function to format datetime
def format_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return dt_str

# Function to create a Stripe account for chefs
def create_stripe_account():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/create-stripe-account-link/",
            method='post',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            return data.get('url')
        else:
            st.error("Failed to create Stripe account link")
            return None
    except Exception as e:
        st.error(f"Error creating Stripe account: {str(e)}")
        logging.error(f"Error creating Stripe account: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to check Stripe account status
def check_stripe_account_status():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/stripe-account-status/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to check Stripe account status")
            return {'has_account': False}
    except Exception as e:
        st.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(traceback.format_exc())
        return {'has_account': False}

# Function to get chef dashboard stats
def get_chef_dashboard_stats():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-dashboard-stats/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to fetch dashboard statistics")
            return {}
    except Exception as e:
        st.error(f"Error fetching dashboard statistics: {str(e)}")
        logging.error(f"Error fetching dashboard statistics: {str(e)}")
        logging.error(traceback.format_exc())
        return {}

# Function to fetch chef meal events
def fetch_chef_meal_events(my_events=False):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/"
        
        # Add query parameter for chef's own events
        if my_events:
            url += "?my_events=true"
            
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            # Ensure we have a valid list of events
            if isinstance(data, list):
                # Verify each event is a dictionary with required fields
                valid_events = []
                for event in data:
                    if isinstance(event, dict) and 'event_date' in event and 'meal' in event:
                        valid_events.append(event)
                    else:
                        logging.error(f"Invalid event format: {event}")
                return valid_events
            else:
                logging.error(f"Expected list of events but got: {type(data)}")
                return []
        else:
            st.error("Failed to fetch chef meal events")
            return []
    except Exception as e:
        st.error(f"Error fetching chef meal events: {str(e)}")
        logging.error(f"Error fetching chef meal events: {str(e)}")
        logging.error(traceback.format_exc())
        return []

# Function to fetch chef meal orders
def fetch_chef_meal_orders(as_chef=False):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/"
        
        # Add query parameter for chef view
        if as_chef:
            url += "?as_chef=true"
            
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to fetch chef meal orders")
            return []
    except Exception as e:
        st.error(f"Error fetching chef meal orders: {str(e)}")
        logging.error(f"Error fetching chef meal orders: {str(e)}")
        logging.error(traceback.format_exc())
        return []

# Function to create a chef meal event
def create_chef_meal_event(data):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Failed to create chef meal event')
                st.error(error_message)
            else:
                st.error("Failed to create chef meal event")
            return None
    except Exception as e:
        st.error(f"Error creating chef meal event: {str(e)}")
        logging.error(f"Error creating chef meal event: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to cancel a chef meal event
def cancel_chef_meal_event(event_id, reason):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/{event_id}/cancel/",
            method='post',
            headers=headers,
            data={'reason': reason}
        )
        
        if response and response.status_code == 200:
            return True
        else:
            st.error("Failed to cancel event")
            return False
    except Exception as e:
        st.error(f"Error cancelling chef meal event: {str(e)}")
        logging.error(f"Error cancelling chef meal event: {str(e)}")
        logging.error(traceback.format_exc())
        return False

# Function to place a chef meal order
def place_chef_meal_order(event_id, quantity, special_requests):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {
            'meal_event': event_id,
            'quantity': quantity,
            'special_requests': special_requests
        }
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Failed to place order')
                st.error(error_message)
            else:
                st.error("Failed to place order")
            return None
    except Exception as e:
        st.error(f"Error placing chef meal order: {str(e)}")
        logging.error(f"Error placing chef meal order: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to cancel a chef meal order
def cancel_chef_meal_order(order_id, reason):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/{order_id}/cancel/",
            method='post',
            headers=headers,
            data={'reason': reason}
        )
        
        if response and response.status_code == 200:
            return True
        else:
            st.error("Failed to cancel order")
            return False
    except Exception as e:
        st.error(f"Error cancelling chef meal order: {str(e)}")
        logging.error(f"Error cancelling chef meal order: {str(e)}")
        logging.error(traceback.format_exc())
        return False

# Function to process payment for a chef meal order
def process_payment(order_id, token):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {'token': token}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/process-chef-meal-payment/{order_id}/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Payment processing failed')
                st.error(error_message)
            else:
                st.error("Payment processing failed")
            return None
    except Exception as e:
        st.error(f"Error processing payment: {str(e)}")
        logging.error(f"Error processing payment: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to format dates in a more user-friendly way
def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%A, %B %d, %Y')
    except:
        return date_str

# Function to fetch chef's meals
def fetch_chef_meals():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/meals/?chef_meals=true",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error("Failed to fetch chef meals")
            return []
    except Exception as e:
        st.error(f"Error fetching chef meals: {str(e)}")
        logging.error(f"Error fetching chef meals: {str(e)}")
        logging.error(traceback.format_exc())
        return []

# Function to handle chef mode toggle
def handle_chef_mode_toggle():
    # Log session state for debugging
    logging.info("Session state keys: %s", list(st.session_state.keys()))
    logging.info("User info in session: %s", 'user_info' in st.session_state)
    logging.info("is_chef in session: %s", 'is_chef' in st.session_state)
    
    if 'is_chef' in st.session_state:
        logging.info("is_chef value: %s", st.session_state['is_chef'])
    else:
        logging.warning("is_chef not found in session state!")
        
    if 'current_role' in st.session_state:
        logging.info("current_role: %s", st.session_state['current_role'])
    else:
        logging.info("current_role not set in session state")
    
    # Check if user is authorized to be a chef
    if 'is_chef' in st.session_state and st.session_state['is_chef']:
        logging.info("User has chef privileges - showing toggle")
        st.sidebar.markdown("### Chef Mode")
        current_role = st.session_state.get('current_role', 'customer')
        
        # Create a toggle in the sidebar
        is_chef_mode = st.sidebar.toggle("Enable Chef Mode", 
                                        value=(current_role == 'chef'),
                                        help="Switch between chef and customer views")
        
        # Update session state if toggle changed
        new_role = 'chef' if is_chef_mode else 'customer'
        if current_role != new_role:
            logging.info("Role switching from %s to %s", current_role, new_role)
            st.session_state['current_role'] = new_role
            # Call API to update backend if needed
            try:
                headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                response = api_call_with_refresh(
                    url=f"{os.getenv('DJANGO_URL')}/meals/api/switch-role/",
                    method='post',
                    headers=headers,
                    data={'role': new_role}
                )
                if response and response.status_code == 200:
                    logging.info("API role switch successful")
                    st.sidebar.success(f"Switched to {new_role} mode!")
                    # Force page rerun to apply changes
                    st.rerun()
                else:
                    error_msg = f"Failed to switch to {new_role} mode. Status: {response.status_code if response else 'No response'}"
                    logging.error(error_msg)
                    st.sidebar.error(error_msg)
            except Exception as e:
                error_msg = f"Error switching modes: {str(e)}"
                st.sidebar.error(error_msg)
                logging.error(error_msg)
                logging.error(traceback.format_exc())
    else:
        logging.info("User does not have chef privileges - not showing toggle")
    return

# Main function for chef meals page
def chef_meals():
    # Check if user is logged in
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        logging.info("User not logged in")
        login_form()
        st.stop()
    else:
        logging.info("User logged in, username: %s", st.session_state.get('username', 'unknown'))

    # Handle chef mode toggle in sidebar
    handle_chef_mode_toggle()
    
    # Check if user is a chef - restrict access to chef role only
    current_role = st.session_state.get('current_role', 'customer')
    logging.info("Current role before access check: %s", current_role)
    
    if current_role != 'chef':
        logging.info("Access denied - user not in chef mode")
        st.warning("This page is only accessible to chefs. Please enable chef mode in the sidebar if you're a chef.")
        if 'is_chef' in st.session_state and st.session_state['is_chef']:
            st.info("You have chef privileges. Enable chef mode using the toggle in the sidebar.")
        st.stop()
    else:
        logging.info("Access granted - user in chef mode")

    # Title and description
    st.title("Chef Meal Management")
    st.write("Create and manage your chef meal events and track orders from customers.")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "My Meal Events", "Received Orders", "Create Event"])
    
    # Tab 1: Chef Dashboard
    with tab1:
        st.header("Chef Dashboard")
        
        # Check Stripe account status
        stripe_status = check_stripe_account_status()
        
        if not stripe_status.get('has_account', False):
            st.warning("You need to set up your Stripe account to receive payments for your meal events.")
            if st.button("Set Up Stripe Account"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
                    st.info("After completing the onboarding, return to this page.")
        elif not stripe_status.get('is_active', False):
            st.warning("Your Stripe account is not fully set up. Please complete the onboarding process.")
            if st.button("Complete Stripe Account Setup"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Click the link below to complete your Stripe account setup:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
                    st.info("After completing the onboarding, return to this page.")
        else:
            st.success("Your Stripe account is active and ready to receive payments!")
        
        # Display dashboard statistics
        stats = get_chef_dashboard_stats()
        
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Upcoming Events", stats.get('upcoming_events_count', 0))
            
            with col2:
                st.metric("Active Orders", stats.get('active_orders_count', 0))
            
            with col3:
                st.metric("Reviews", stats.get('review_count', 0))
            
            with col4:
                st.metric("Average Rating", f"{stats.get('avg_rating', 0):.1f}★")
            
            st.subheader("Revenue")
            st.info(f"Monthly Revenue: {format_currency(stats.get('revenue_this_month', 0))}")
            
            # Add a placeholder for future charts
            st.subheader("Order History")
            st.info("Detailed analytics coming soon!")
    
    # Tab 2: My Meal Events
    with tab2:
        st.header("My Meal Events")
        
        # Fetch chef's meal events
        events = fetch_chef_meal_events(my_events=True)
        
        if events:
            try:
                # Split into upcoming and past events
                now = datetime.now().date()
                upcoming_events = []
                past_events = []
                
                for event in events:
                    if not isinstance(event, dict):
                        logging.error(f"Event is not a dictionary: {event}")
                        continue
                        
                    if 'event_date' not in event:
                        logging.error(f"Event missing event_date: {event}")
                        continue
                        
                    try:
                        event_date = datetime.strptime(event['event_date'], '%Y-%m-%d').date()
                        if event_date >= now:
                            upcoming_events.append(event)
                        else:
                            past_events.append(event)
                    except (ValueError, TypeError) as e:
                        logging.error(f"Invalid date format: {event['event_date']} - {str(e)}")
                        continue
                
                # Display upcoming events
                if upcoming_events:
                    st.subheader("Upcoming Events")
                    for event in upcoming_events:
                        with st.expander(f"{event['meal']['name']} - {format_date(event['event_date'])}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Event Date:** {format_date(event['event_date'])}")
                                st.markdown(f"**Event Time:** {event['event_time']}")
                                st.markdown(f"**Order Cutoff:** {format_datetime(event['order_cutoff_time'])}")
                                st.markdown(f"**Status:** {event['status'].capitalize()}")
                            
                            with col2:
                                st.markdown(f"**Base Price:** {format_currency(event['base_price'])}")
                                st.markdown(f"**Current Price:** {format_currency(event['current_price'])}")
                                st.markdown(f"**Orders:** {event['orders_count']}/{event['max_orders']}")
                                
                                # Cancel button if event is still upcoming
                                if event['status'] not in ['cancelled', 'completed']:
                                    if st.button(f"Cancel Event", key=f"cancel_{event['id']}"):
                                        reason = st.text_area("Reason for cancellation", key=f"reason_{event['id']}")
                                        if st.button(f"Confirm Cancellation", key=f"confirm_{event['id']}"):
                                            if cancel_chef_meal_event(event['id'], reason):
                                                st.success("Event cancelled successfully!")
                                                st.rerun()
                            
                            st.markdown(f"**Description:** {event['description']}")
                            if event['special_instructions']:
                                st.markdown(f"**Special Instructions:** {event['special_instructions']}")
                else:
                    st.info("You don't have any upcoming meal events.")
                
                # Display past events
                if past_events:
                    st.subheader("Past Events")
                    past_df = pd.DataFrame([
                        {
                            'Event Date': format_date(e['event_date']),
                            'Meal': e['meal']['name'],
                            'Orders': e['orders_count'],
                            'Revenue': format_currency(float(e['current_price']) * e['orders_count']),
                            'Status': e['status'].capitalize()
                        } for e in past_events
                    ])
                    
                    st.dataframe(past_df)
            except Exception as e:
                st.error(f"Error processing meal events: {str(e)}")
                logging.error(f"Error processing meal events: {str(e)}")
                logging.error(traceback.format_exc())
        else:
            st.info("You haven't created any meal events yet.")
            st.button("Create your first meal event", on_click=lambda: st.session_state.update({'active_tab': 'Create Event'}))
    
    # Tab 3: Received Orders
    with tab3:
        st.header("Received Orders")
        
        # Fetch orders as chef
        orders = fetch_chef_meal_orders(as_chef=True)
        
        if orders:
            # Split into active and past orders
            active_orders = [o for o in orders if o['status'] in ['placed', 'confirmed']]
            completed_orders = [o for o in orders if o['status'] == 'completed']
            cancelled_orders = [o for o in orders if o['status'] in ['cancelled', 'refunded']]
            
            # Display active orders
            if active_orders:
                st.subheader("Active Orders")
                for order in active_orders:
                    with st.expander(f"Order #{order['id']} - {order['customer']['username']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Meal:** {order['meal_event']['meal']['name']}")
                            st.markdown(f"**Event Date:** {format_date(order['meal_event']['event_date'])}")
                            st.markdown(f"**Quantity:** {order['quantity']}")
                            st.markdown(f"**Price Paid:** {format_currency(float(order['price_paid']) * order['quantity'])}")
                        
                        with col2:
                            st.markdown(f"**Status:** {order['status'].capitalize()}")
                            st.markdown(f"**Order Date:** {format_datetime(order['created_at'])}")
                            
                            # Button to mark as completed if event date has passed
                            event_date = datetime.strptime(order['meal_event']['event_date'], '%Y-%m-%d').date()
                            if order['status'] == 'confirmed' and event_date <= datetime.now().date():
                                if st.button(f"Mark as Completed", key=f"complete_{order['id']}"):
                                    # Implement the completion logic here
                                    st.success("Order marked as completed!")
                                    st.rerun()
                        
                        if order['special_requests']:
                            st.markdown(f"**Special Requests:** {order['special_requests']}")
            else:
                st.info("You don't have any active orders.")
            
            # Display completed orders in a table
            if completed_orders:
                st.subheader("Completed Orders")
                completed_df = pd.DataFrame([
                    {
                        'Order Date': format_datetime(o['created_at']),
                        'Customer': o['customer']['username'],
                        'Meal': o['meal_event']['meal']['name'],
                        'Quantity': o['quantity'],
                        'Total': format_currency(float(o['price_paid']) * o['quantity'])
                    } for o in completed_orders
                ])
                
                st.dataframe(completed_df)
            
            # Display cancelled orders in a table
            if cancelled_orders:
                st.subheader("Cancelled Orders")
                cancelled_df = pd.DataFrame([
                    {
                        'Order Date': format_datetime(o['created_at']),
                        'Customer': o['customer']['username'],
                        'Meal': o['meal_event']['meal']['name'],
                        'Status': o['status'].capitalize(),
                        'Refunded': 'Yes' if o['status'] == 'refunded' else 'No'
                    } for o in cancelled_orders
                ])
                
                st.dataframe(cancelled_df)
        else:
            st.info("You haven't received any orders yet.")
    
    # Tab 4: Create Event
    with tab4:
        st.header("Create a Meal Event")
        
        # Check if Stripe account is active
        stripe_status = check_stripe_account_status()
        if not stripe_status.get('is_active', False):
            st.warning("You need to set up your Stripe account before creating meal events.")
            if st.button("Set Up Stripe Account", key="setup_stripe_create"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
            return
        
        # Fetch chef's meals
        meals = fetch_chef_meals()
        
        if not meals:
            st.warning("You need to create meals before you can create meal events.")
            return
        
        # Create form for new meal event
        with st.form("create_meal_event_form"):
            meal_options = {m['id']: m['name'] for m in meals}
            meal_id = st.selectbox("Select Meal", options=list(meal_options.keys()), format_func=lambda x: meal_options[x])
            
            col1, col2 = st.columns(2)
            
            with col1:
                event_date = st.date_input("Event Date", min_value=datetime.now().date() + timedelta(days=1))
                event_time = st.time_input("Event Time", value=datetime.now().time().replace(hour=18, minute=0))
                order_cutoff_time = st.time_input("Order Cutoff Time", value=datetime.now().time().replace(hour=12, minute=0))
            
            with col2:
                base_price = st.number_input("Base Price ($)", min_value=5.0, step=1.0, value=15.0)
                min_price = st.number_input("Minimum Price ($)", min_value=1.0, max_value=base_price, step=1.0, value=max(5.0, base_price * 0.7))
                max_orders = st.number_input("Maximum Orders", min_value=1, step=1, value=10)
                min_orders = st.number_input("Minimum Orders", min_value=1, max_value=max_orders, step=1, value=3)
            
            description = st.text_area("Event Description", placeholder="Describe your meal event...")
            special_instructions = st.text_area("Special Instructions (Optional)", placeholder="Any special instructions for customers...")
            
            submit_button = st.form_submit_button("Create Meal Event")
        
        if submit_button:
            # Format the date and cutoff time
            cutoff_datetime = datetime.combine(event_date, order_cutoff_time)
            
            # Prepare the data
            data = {
                'meal': meal_id,
                'event_date': event_date.strftime('%Y-%m-%d'),
                'event_time': event_time.strftime('%H:%M'),
                'order_cutoff_time': cutoff_datetime.strftime('%Y-%m-%d %H:%M'),
                'base_price': base_price,
                'min_price': min_price,
                'max_orders': max_orders,
                'min_orders': min_orders,
                'description': description,
                'special_instructions': special_instructions
            }
            
            # Create the meal event
            result = create_chef_meal_event(data)
            
            if result:
                st.success("Meal event created successfully!")
                st.rerun()

# Entry point
if __name__ == "__main__":
    chef_meals()
