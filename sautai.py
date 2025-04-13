import streamlit as st
import os
import logging
from dotenv import load_dotenv
import sys
import traceback

# Add the current directory to the Python path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import from utils with the modified path
try:
    from utils import display_chef_toggle_in_sidebar
except ImportError as e:
    # Fallback definition if import still fails
    def display_chef_toggle_in_sidebar():
        """Fallback implementation if the utils module can't be imported"""
        if 'is_chef' in st.session_state and st.session_state['is_chef']:
            st.sidebar.markdown("### Chef Access")
            current_role = st.session_state.get('current_role', 'customer')
            is_chef_mode = st.sidebar.toggle(
                "Enable Chef Mode", 
                value=(current_role == 'chef'),
                help="Switch between chef and customer views"
            )
            # Handle role switching (simplified version)
            if (is_chef_mode and current_role != 'chef') or (not is_chef_mode and current_role != 'customer'):
                st.sidebar.info("Please refresh the page to apply the role change.")


# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log', 
    filemode='w'
)

def main():
    # Set page config once in the main entry point
    st.set_page_config(
        page_title="sautAI - Your Diet and Nutrition Guide",
        page_icon="🍲", 
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            'Report a bug': "mailto:support@sautai.com",
            'About': """
            # Welcome to sautAI 🍲
            
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
    
    # Add custom CSS for logo responsiveness and improved visibility
    st.markdown("""
    <style>
    .logo-container {
        padding: 10px;
        text-align: center;
    }
    .header-text {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .header-subtext {
        font-size: 1.1rem;
    }
    @media (max-width: 768px) {
        .header-text {
            font-size: 1.5rem !important;
        }
        .header-subtext {
            font-size: 0.9rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Add app logo with more prominence - adjusted column ratio for better balance
    header_col1, header_col2 = st.columns([0.3, 0.7])
    with header_col1:
        # Use st.image for more reliable image loading
        st.image("images/sautai_logo.PNG", width=250)
    with header_col2:
        st.markdown('<h1 class="header-text">sautAI</h1>', unsafe_allow_html=True)
        st.markdown('<p class="header-subtext">Your personal diet and nutrition assistant</p>', unsafe_allow_html=True)
    
    st.markdown("---")  # Add a horizontal rule for separation
    
    # Screen size detection JavaScript
    st.components.v1.html("""
    <script>
        // Detect screen width and send to Streamlit
        const setScreenSizeState = () => {
            const isDesktop = window.innerWidth >= 768;
            const data = {
                isDesktop: isDesktop
            };
            // Use Streamlit's setComponentValue to pass the data
            if (window.parent.streamlitAPIReady) {
                window.parent.Streamlit.setComponentValue(data);
            }
        };
        
        // Run on load and on resize
        window.addEventListener('load', setScreenSizeState);
        window.addEventListener('resize', setScreenSizeState);
    </script>
    """, height=0)
    
    # Make sure _is_desktop is initialized (default to desktop view)
    if '_is_desktop' not in st.session_state:
        st.session_state._is_desktop = True
    
    # Determine pages to show based on login status
    def get_pages():
        pages = []
        # Basic pages for all users
        pages.append(st.Page("views/home.py", title="Home"))
        
        # Only show these pages if logged in
        pages.append(st.Page("views/1_assistant.py", title="Assistant", icon="🥘"))
        # Always show meal plans (we'll handle auth within the page)
        # Only show meal plans if user is not a chef or if they're a chef but in customer role
        if not (st.session_state.get("is_chef", False) and st.session_state.get("current_role", "customer") == "chef"):
            pages.append(st.Page("views/2_meal_plans.py", title="Meal Plans", icon="📅"))
        # Check if there are activation or password reset parameters in the URL
        uid = st.query_params.get("uid", "")
        token = st.query_params.get("token", "")
        action = st.query_params.get("action", "")
        
        # If there are activation parameters, include the activation page
        # This is a "hidden" page that won't show in nav but can be accessed by activation link
        if uid and token and (action == 'activate' or action == 'password_reset'):
            pages.append(st.Page("views/5_account.py", title="Account Activation", icon="✅"))
        
        
        if st.session_state.get("is_logged_in", False):
            # Check if user is in chef mode
            current_role = st.session_state.get("current_role", "customer")
            
            if current_role == "chef" and st.session_state.get("is_chef", False):
                # Only show chef-relevant pages when in chef mode
                pages.append(st.Page("views/8_chef_meals.py", title="Chef Dashboard", icon="👨‍🍳"))
                pages.append(st.Page("views/5_account.py", title="My Account", icon="⚙️"))
                pages.append(st.Page("views/6_profile.py", title="Profile", icon="🪪"))
            else:
                # Show regular user pages when not in chef mode
                pages.append(st.Page("views/3_pantry.py", title="Pantry", icon="🏪"))
                pages.append(st.Page("views/4_history.py", title="Chat History", icon="💬"))
                pages.append(st.Page("views/5_account.py", title="My Account", icon="⚙️"))
                pages.append(st.Page("views/6_profile.py", title="Profile", icon="🪪"))
                # Only show chef application page if explicitly requested
                if st.session_state.get("show_chef_application", False):
                    pages.append(st.Page("views/chef_application.py", title="Chef Application", icon="👨‍🍳"))
        else:
            # Show register page if not logged in
            pages.append(st.Page("views/7_register.py", title="Register", icon="📝"))
            
        
        return pages
    
    # Get navigation pages and store in session state for access from other files
    pages = get_pages()
    st.session_state["navigation"] = pages
    
    # Display chef toggle in sidebar if user has chef privileges
    display_chef_toggle_in_sidebar()
    
    # Initialize navigation
    try:
        pg = st.navigation(get_pages())
        pg.run()  # Run the selected page
    except Exception as e:
        logging.error(f"Navigation error: {str(e)}")

        traceback.print_exc()
        st.error("Navigation error occurred. Please try refreshing the page.")
    

if __name__ == "__main__":
    main() 