
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
from sqlalchemy import Engine, create_engine,text
from sqlalchemy.pool import StaticPool
from langchain_openai import ChatOpenAI



def get_engine_for_mysql_db(db_uri, mysql_host, mysql_user, mysql_password,mysql_db) -> Engine:
    engine = create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}")
    return engine

def main():
    # Example function to execute a query on MySQL database
    engine = get_engine_for_mysql_db('','localhost:3306', 'root','AmiSam%40123','employees')
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM employees LIMIT 5;"))
        for row in result:
            print(row)
        connection.close()

if __name__ == "__main__":
    main()