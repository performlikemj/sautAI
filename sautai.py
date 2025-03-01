import streamlit as st
import os
import logging
from dotenv import load_dotenv
import sys
import traceback

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
    st.markdown("""
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
    """, unsafe_allow_html=True)
    
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
        if st.session_state.get("is_logged_in", False):
            pages.append(st.Page("views/2_meal_plans.py", title="Meal Plans", icon="📅"))
            pages.append(st.Page("views/3_pantry.py", title="Pantry", icon="🏪"))
            if st.session_state.get("is_chef", False):
                pages.append(st.Page("views/8_chef_meals.py", title="Chef Dashboard", icon="👨‍🍳"))
            pages.append(st.Page("views/4_history.py", title="Chat History", icon="💬"))
            pages.append(st.Page("views/5_account.py", title="My Account", icon="⚙️"))
            pages.append(st.Page("views/6_profile.py", title="Profile", icon="🪪"))
        else:
            # Show register page if not logged in
            pages.append(st.Page("views/7_register.py", title="Register", icon="📝"))
        
        return pages
    
    # Get navigation pages and store in session state for access from other files
    pages = get_pages()
    st.session_state["navigation"] = pages
    
    # Initialize navigation
    try:
        pg = st.navigation(get_pages())
        pg.run()  # Run the selected page
    except Exception as e:
        logging.error(f"Navigation error: {str(e)}")
        print(f"Navigation error: {str(e)}")
        traceback.print_exc()
        st.error("Navigation error occurred. Please try refreshing the page.")
    

if __name__ == "__main__":
    main() 