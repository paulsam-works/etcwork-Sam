import asyncio
from pathlib import Path
from database.database_utility import configure_database
from teams.database_team import get_database_team
from langchain.sql_database import SQLDatabase
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
import streamlit as st

st.title("DatabaseGenie: Multi Modal DataBase Analyzer 🚀 ")
st.write("Welcome to DatabaseGenie, your personal Database Query Analyzer 🚀 Here you can ask solutions to various database related problems.")

task = st.text_input("Enter your Database problem or Question:",value="List of tables from sales database.")

async def run():
    print(" Execution Started ......")
    dbfilepath = (Path(__file__).parent/"database/sales.db").absolute()
    print('Database Path :',dbfilepath)
    #MYSQL_DB = 'MySQL'
    #SQLITE_DB = 'SQLite' 'localhost:3306', 'root','AmiSam%40123','employees'
    selected_database ='SQLite' 
    database_uri = 'sales.db'
    database_host ='localhost:3306'
    database_user = 'root'
    database_password = 'AmiSam%40123'
    database_name ='employees'

    # user input .. taken from user end .
    database = configure_database(selected_database, database_uri, database_host, database_user, database_password, database_name)

      
    try:
        database_team = get_database_team(database)
        async for message in database_team.run_stream(task=task):
            if isinstance(message, TextMessage):
                print(msg:=f"{message.source} : {message.content}")
                yield msg
            elif isinstance(message, TaskResult):
                print(msg:=f"Stop Reason : {message.stop_reason}")
                yield msg
        print('=='*20)
        print("Task Completed Successfully.")
    except Exception as e:
        print(f"Error occurred: {e}")
        yield f"Error occurred: {e}"
    finally:
        print(" Stopping Docker container ..")


if st.button("Run"):
    st.write("Running the task...")

    print(" Execution Started ......")
    # dbfilepath = (Path(__file__).parent/"database/sales.db").absolute()
    # print('Database Path :',dbfilepath)
    # #MYSQL_DB = 'MySQL'
    # #SQLITE_DB = 'SQLite' 'localhost:3306', 'root','AmiSam%40123','employees'
    # selected_database ='SQLite' 
    # database_uri = 'sales.db'
    # database_host ='localhost:3306'
    # database_user = 'root'
    # database_password = 'AmiSam%40123'
    # database_name ='employees'

    # user input .. taken from user end .
    # database = configure_database(selected_database, database_uri, database_host, database_user, database_password, database_name)


    # database_team = get_database_team(database)

    async def collect_messages():
        async for msg in run():
            if isinstance(msg, str):
                if msg.startswith("User_Agent"):
                    with st.chat_message('User',avatar="🧑"):
                        st.markdown(msg)
                elif msg.startswith("Db_Planner_Agent"):
                    with st.chat_message('Planner',avatar="🤖"):
                        st.markdown(msg)
                elif msg.startswith("MySql_Agent"):
                    with st.chat_message('MySql Agent',avatar="🤖"):
                        st.markdown(msg)
                elif msg.startswith("Sqlite3_Agent"):
                    with st.chat_message('Sqlite3 Agent',avatar="💻"):
                        st.markdown(msg)
            elif isinstance(msg,TaskResult):
                with st.chat_message('stopper',avatar="🛑"):
                    st.markdown(f"Task Completed: {msg.result}")
    
    asyncio.run(collect_messages())
