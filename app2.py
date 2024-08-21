import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq  # Import Groq LLM
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Automatically retrieve the Groq API key from the environment variables
api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="SkyChat", page_icon="👽")
st.title("👽SkyChat: Chat with Database")

# Custom CSS for font colors and styles
st.markdown("""
    <style>
    .stTextInput, .stTextArea, .stChatMessage, .stButton, .stSelectbox, .stRadio, .stSidebar > div {
        color: #ffffff;
    }
    .stMarkdown p {
        color: #ffffff;
    }
    .stTitle h1 {
        color: #ffa500;  /* Orange color for title */
    }
    .stSidebar h1, .stSidebar h2, .stSidebar h3 {
        color: #00ff00;  /* Green color for sidebar headings */
    }
    .stSidebar .stTextInput, .stSidebar .stTextArea, .stSidebar .stButton, .stSidebar .stSelectbox, .stSidebar .stRadio {
        color: #00ff00;  /* Green color for sidebar inputs */
    }
    body {
        background-color: #000000;  /* Black background */
    }
    </style>
    """, unsafe_allow_html=True)

LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"

radio_opt = ["Use SQLite 3 Database - Student.db", "Connect to your MySQL Database"]

selected_opt = st.sidebar.radio(label="Choose the DB which you want to chat with", options=radio_opt)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("Provide MySQL Host")
    mysql_user = st.sidebar.text_input("MySQL User")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database")
else:
    db_uri = LOCALDB

# Inform the user if the API key is missing
if not api_key:
    st.error("Groq API key is missing. Please ensure it's set in the .env file.")
    st.stop()

# LLM model
llm = ChatGroq(groq_api_key=api_key, model_name="Llama3-8b-8192", streaming=True)

@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).parent / "student.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))

if db_uri == MYSQL:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
else:
    db = configure_db(db_uri)

# Toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# Initialize or clear message history
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

# Display chat messages using st.chat_message with custom colors
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"], unsafe_allow_html=True)
    else:
        st.chat_message("assistant").write(msg["content"], unsafe_allow_html=True)

# Handle user input
user_query = st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state["messages"].append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query, unsafe_allow_html=True)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state["messages"].append({"role": "assistant", "content": response})
        st.write(response, unsafe_allow_html=True)
