
import streamlit as st
import requests

# Page configuration
st.set_page_config(
    page_title="DataSage",
    page_icon="📊",
    layout="wide"
)

# FastAPI backend URL
API_URL = "http://127.0.0.1:8000/chat"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Application title
st.title("📊 DataSage")
st.caption("Your Intelligent Multi-Agent Data Platform")

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
user_question = st.chat_input("Ask DataSage anything about your data...")

if user_question:

    # Display user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_question
    })

    with st.chat_message("user"):
        st.markdown(user_question)

    # Get response from FastAPI
    with st.chat_message("assistant"):
        with st.spinner("DataSage is thinking..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"message": user_question},
                    timeout=120
                )

                response.raise_for_status()
                answer = response.json()["response"]

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection failed: {e}")
