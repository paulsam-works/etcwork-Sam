import streamlit as st
from teams.dsa_team import get_dsa_team_and_docker
from config.docker_utils import start_docker_container, stop_docker_container
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
import asyncio



st.title("CodeGenie: AI-Powered Code Generation and Execution")
st.write("Welcome to CodeGenie, your personal DSA problem solver 🚀 Here you can ask solutions to various data structures and algorithm problems.")

task = st.text_input("Enter your DSA problem or Question:",value="Write a python code to multiply two numbers.")

async def run(team, docker,task):
    try:
        await start_docker_container(docker)
        async for message in team.run_stream(task=task):
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
        await stop_docker_container(docker)
    
if st.button("Run"):
    st.write("Running the task...")

    dsa_team, docker = get_dsa_team_and_docker()

    async def collect_messages():
        async for msg in run(dsa_team, docker, task):
            if isinstance(msg, str):
                if msg.startswith("user"):
                    with st.chat_message('user',avatar="🧑"):
                        st.markdown(msg)
                elif msg.startswith("DSA_Problem_Solver_Agent"):
                    with st.chat_message('assistant',avatar="🤖"):
                        st.markdown(msg)
                elif msg.startswith("Code_Executor_Agent"):
                    with st.chat_message('assistant',avatar="💻"):
                        st.markdown(msg)
            elif isinstance(msg,TaskResult):
                with st.chat_message('stopper',avatar="🛑"):
                    st.markdown(f"Task Completed: {msg.result}")
    
    asyncio.run(collect_messages())

