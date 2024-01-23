# pages/activate.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def activate():
    st.title("Account Activation")
    
    uid = st.query_params.get("uid", [""])[0]
    token = st.query_params.get("token", [""])[0]

    if st.button("Activate Account"):
        response = requests.post(f'{os.getenv("DJANGO_URL")}/auth/api/register/verify-email/', data={'uid': uid, 'token': token})
        if response.status_code == 200:
            st.success("Account activated successfully!")
            st.switch_page("pages/assistant.py")
        else:
            st.error("Account activation failed.")

if __name__ == "__main__":
    activate()
