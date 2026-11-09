
import streamlit as st
import requests

# -------------------- PAGE CONFIGURATION --------------------

st.set_page_config(
    page_title="DataSage",
    page_icon="📊",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000/chat"


# -------------------- SESSION INITIALIZATION --------------------

if "chats" not in st.session_state:
    st.session_state.chats = {
        "Chat 1": []
    }

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 1

if "last_route" not in st.session_state:
    st.session_state.last_route = None


# -------------------- SIDEBAR --------------------

with st.sidebar:

    st.title("📊 DataSage")
    st.caption("Multi-Agent Data Platform")

    st.divider()

    # Create a new conversation
    if st.button("➕ New Chat", use_container_width=True):

        st.session_state.chat_counter += 1

        new_chat = f"Chat {st.session_state.chat_counter}"

        st.session_state.chats[new_chat] = []
        st.session_state.current_chat = new_chat
        st.session_state.last_route = None

        st.rerun()

    # Select an existing conversation
    st.subheader("Your Conversations")

    st.selectbox(
        "Select Chat",
        options=list(st.session_state.chats.keys()),
        key="current_chat"
    )

    # Clear current conversation
    if st.button("🗑️ Clear Current Chat", use_container_width=True):

        st.session_state.chats[st.session_state.current_chat] = []
        st.session_state.last_route = None

        st.rerun()

    st.divider()

    # Latest routing information
    st.subheader("Agent Status")

    if st.session_state.last_route == "sql":

        st.success("SQL Analyst")

        st.caption("Handling database queries")

    elif st.session_state.last_route == "etl":

        st.info("ETL Analyst")

        st.caption("Handling data extraction and transformation")

    else:

        st.caption("Waiting for your first query...")


# -------------------- MAIN APPLICATION --------------------

st.title("📊 DataSage")

st.caption("Your Intelligent Multi-Agent Data Platform")

st.divider()


# Get messages for the selected conversation
messages = st.session_state.chats[st.session_state.current_chat]


# -------------------- DISPLAY CHAT HISTORY --------------------

for message in messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        # Show which agent handled the request
        if message["role"] == "assistant" and message.get("route_used"):

            route = message["route_used"]

            if route == "sql":
                st.caption("🔍 Handled by SQL Analyst")

            elif route == "etl":
                st.caption("⚙️ Handled by ETL Analyst")


# -------------------- CHAT INPUT --------------------

user_question = st.chat_input(
    "Ask DataSage anything about your data..."
)


if user_question:

    # Store user message
    messages.append({
        "role": "user",
        "content": user_question
    })

    # Display user message
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

                result = response.json()

                answer = result["response"]
                route_used = result["route_used"]

                # Store latest routing decision
                st.session_state.last_route = route_used

                # Display answer
                st.markdown(answer)

                if route_used == "sql":
                    st.caption("🔍 Handled by SQL Analyst")

                elif route_used == "etl":
                    st.caption("⚙️ Handled by ETL Analyst")

                # Store assistant response
                messages.append({
                    "role": "assistant",
                    "content": answer,
                    "route_used": route_used
                })

            except requests.exceptions.RequestException as e:

                error_message = f"Backend connection failed: {e}"

                st.error(error_message)

                messages.append({
                    "role": "assistant",
                    "content": error_message
                })

    # Refresh to update sidebar and chat history
    st.rerun()
