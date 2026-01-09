from autogen_agentchat.agents import AssistantAgent
from config.settings import get_model_client
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import Engine, create_engine
from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI


# get the model client
model_client = get_model_client()


def get_mysql_agent():
    mysql_tool = get_mysql_tools()
    mysql_agent = AssistantAgent(
        name = "MySql_Agent",
        model_client = model_client,
        system_message ="""You are an intelligent MySql agent. You generate and execute SQL queries to retrieve data based on instructions from the 'Planner'.
        You use the `mysql_tool` to interact with the database.
        Use database employees for your queries.
        While building the sql queries check all related tables and associate them to find out the correct answer
        Your response should contain the SQL query and the query results.
        Respond with 'TERMINATE' if the task is completed.
        """
    )
    #mysql_agent.register_tool(mysql_tool)
    return mysql_agent

def get_mysql_tools():
    
    #get the engine for mysql database
    dbase1= get_engine_for_mysql_db('','localhost:3306', 'root','AmiSam%40123','employees')
    llm = ChatOpenAI(model='gpt-4o', temperature = 0, api_key='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')
    mysql_toolkit = SQLDatabaseToolkit(db=dbase1, llm=llm)
    # Create the LangChain tool adapter for every tool in the toolkit.
    tools1 = [LangChainToolAdapter(tool) for tool in mysql_toolkit.get_tools()]
    return tools1

def get_engine_for_mysql_db(db_uri:str, mysql_host:str, mysql_user:str, mysql_password:str,mysql_db:str) -> Engine:
    engine = SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))
    return engine
