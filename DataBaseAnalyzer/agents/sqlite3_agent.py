import asyncio
import sqlite3
import requests
from dotenv import load_dotenv
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from autogen_agentchat.base import TaskResult
from autogen_agentchat.ui import Console
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool
from langchain_openai import ChatOpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def get_engine_for_mysql_db(db_uri:str, mysql_host:str, mysql_user:str, mysql_password:str,mysql_db:str) -> Engine:
    engine = SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))
    return engine

def get_engine_for_chinook_db() -> Engine:
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(sql_script)
    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

async def team_config():
    # get the engine for Chinook database
    engine = get_engine_for_chinook_db()
    dbase = SQLDatabase(engine=engine)

    # get the engine for mysql database
    dbase1= get_engine_for_mysql_db('','localhost:3306', 'root','AmiSam%40123','employees')

    llm = ChatOpenAI(model='gpt-4o', temperature = 0, api_key=OPENAI_API_KEY)
    toolkit = SQLDatabaseToolkit(db=dbase, llm=llm)
    toolkit1 = SQLDatabaseToolkit(db=dbase1, llm=llm)


    model_client = OpenAIChatCompletionClient(model = 'gpt-4o', api_key = OPENAI_API_KEY)
    
    # Create the LangChain tool adapter for every tool in the toolkit.
    tools = [LangChainToolAdapter(tool) for tool in toolkit.get_tools()]
    tools1 = [LangChainToolAdapter(tool) for tool in toolkit1.get_tools()]


    # Defining our Agents
    sqlite3_agent = AssistantAgent(
        name = "Sqlite3_Agent",
        model_client = model_client,
        description = "An AI Sqlite3 Database Agent that generate and execute SQL queries to retrieve data from Chinook database based on instructions from the given task.",
        system_message ="""You are an intelligent Sqlite3 agent. You generate and execute SQL queries to retrieve data based on instructions from the 'Planner'.
        You use the `sqlite_tool` to interact with the database.
        Your response should contain the SQL query and the query results.
        Respond with 'TERMINATE' if the task is completed.
        """
    )

      # Defining our Agents
    mysql_agent = AssistantAgent(
        name = "Mysql_Agent",
        model_client = model_client,
        description = "An AI MySQL Database Agent that generate and execute SQL queries to retrieve data from employees database based on instructions from the given task.",
        system_message ="""You are an intelligent MySql agent. You generate and execute SQL queries to retrieve data based on instructions from the 'Planner'.
        You use the `mysql_tool` to interact with the database.
        Use database employees for your queries.
        While building the sql queries check all related tables and associate them to find out the correct answer
        Your response should contain the SQL query and the query results.
        Respond with 'TERMINATE' if the task is completed.
        """
    )


    terminate_condition = TextMentionTermination(text = "TERMINATE")

    team = RoundRobinGroupChat(
        participants = [sqlite3_agent],
        termination_condition = terminate_condition
    )
    team1 = RoundRobinGroupChat(
        participants = [mysql_agent],
        termination_condition = terminate_condition
    )
    return team1

async def news_session(team):
# running the session 
    async for message in team.run_stream(task='Can you tell me the maximum salary of Georgi Facello emp_no=10001 from employees database? '):
        if isinstance(message,TaskResult):
            message = f'News Session completed with {message.stop_reason}'
            yield message
        else:
            message = f'{message.source}: {message.content}'
            yield message

async def main():
    team = await team_config()

    async for message in news_session(team):
        print('-'*70)
        print((message))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())