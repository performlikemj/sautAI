"""
Voice input component for adding pantry items using OpenAI's Whisper API.
This module integrates with the main pantry management page.
"""
import streamlit as st
import os
import logging
import tempfile
from datetime import date
from utils import api_call_with_refresh

def add_pantry_item_from_voice():
    """
    Display a voice input widget for adding pantry items and process the recorded audio
    using the backend API that leverages OpenAI's Whisper API.
    """
    st.subheader("Add Pantry Item with Voice", anchor=False)
    
    # Expandable section with instructions
    with st.expander("How to use voice input"):
        st.markdown("""
        **Tips for best results:**
        - Speak clearly into your microphone
        - Mention all required details:
          - Item name (e.g., "black beans")
          - Quantity (e.g., "3 cans")
          - Expiration date if known (e.g., "expires December 2025")
          - Type ("canned" or "dry goods")
        - Optional: Add any special notes
        
        **Example:** "Two cans of organic black beans, expires January 15th, 2025. Canned goods."
        """)
    
    # Audio input widget
    audio_data = st.audio_input("Record your pantry item description", key="pantry_voice_input")
    
    if audio_data:
        # Display the recorded audio
        st.audio(audio_data, format="audio/wav")
        
        # Button to process the audio
        if st.button("Add to Pantry", key="process_voice_btn", type="primary"):
            with st.spinner("Processing your audio..."):
                try:
                    # Save the audio data to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                        temp_audio.write(audio_data.getvalue())
                        temp_audio_path = temp_audio.name
                    
                    # Send the audio file to the backend API
                    with open(temp_audio_path, 'rb') as audio_file:
                        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                        files = {'audio_file': audio_file}
                        
                        response = api_call_with_refresh(
                            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/from-audio/',
                            method='post',
                            headers=headers,
                            files=files
                        )
                    
                    # Clean up the temporary file
                    os.unlink(temp_audio_path)
                    
                    # Process the response
                    if response and response.status_code == 201:
                        result = response.json()
                        
                        # Display the results in a success message
                        st.success(f"Added '{result['pantry_item']['item_name']}' to your pantry!")
                        
                        # Create tabs to show details
                        transcription_tab, details_tab = st.tabs(["What I Heard", "Item Details"])
                        
                        with transcription_tab:
                            st.markdown(f"**Transcription:** {result['transcription']}")
                        
                        with details_tab:
                            pantry_item = result['pantry_item']
                            
                            # Format expiration date for display
                            expiration = pantry_item.get('expiration_date', 'Not specified')
                            if expiration is None:
                                expiration = 'Not specified'
                            
                            # Display item details in a table format
                            st.markdown(f"""
                            | Property | Value |
                            | --- | --- |
                            | Item | **{pantry_item['item_name']}** |
                            | Quantity | {pantry_item['quantity']} |
                            | Type | {pantry_item['item_type']} |
                            | Expiration | {expiration} |
                            """)
                            
                            if pantry_item.get('notes'):
                                st.markdown(f"**Notes:** {pantry_item['notes']}")
                            
                        # Add a refresh button to clear and prepare for another entry
                        if st.button("Add Another Item", key="add_another_voice"):
                            st.rerun()
                    
                    else:
                        # Handle errors from the API
                        error_message = "An error occurred while processing your audio."
                        if response:
                            try:
                                error_data = response.json()
                                error_details = error_data.get('details', '')
                                error_message = f"{error_data.get('error', 'Error')}: {error_details}"
                            except:
                                error_message = f"Error: HTTP {response.status_code}"
                        
                        st.error(error_message)
                        logging.error(f"Voice pantry item error: {error_message}")
                
                except Exception as e:
                    st.error(f"Error processing audio: {str(e)}")
                    logging.error(f"Exception in voice pantry processing: {str(e)}")

def pantry_voice_tab():
    """
    Wrapper function to create a tab for voice-based pantry additions.
    Can be integrated into the main pantry page.
    """
    add_pantry_item_from_voice()

# Example of how to integrate with the main app
if __name__ == "__main__":
    # This is a standalone test when running this file directly
    st.set_page_config(page_title="Voice Pantry Test", page_icon="🎙️")
    
    # Mock the authentication
    if 'user_info' not in st.session_state:
        st.session_state.user_info = {"access": "test_token"}
    
    st.title("Pantry Voice Input Test")
    pantry_voice_tab() 