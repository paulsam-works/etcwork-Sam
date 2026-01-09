from autogen_agentchat.agents import AssistantAgent
from config.settings import get_model_client
from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase





def get_sqlite3_tools(database,model_client):
     
     llm = ChatOpenAI(model='gpt-4o', temperature = 0, api_key='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')

     toolkit = SQLDatabaseToolkit(db=database, llm=llm)
     # Create the LangChain tool adapter for every tool in the toolkit.
     tools = [LangChainToolAdapter(tool) for tool in toolkit.get_tools()]
     return tools

def get_sqlite_agent(database):
    # Defining our Agents
    # get the model client
    model_client = get_model_client()

    sqlite3_tools = get_sqlite3_tools(database,model_client)

    sqlite3_agent = AssistantAgent(
        name = "Sqlite3_Agent",
        model_client = model_client,
        description = "An AI Sqlite3 Database Agent that generate and execute SQL queries to retrieve data from sales database based on instructions from the given task.",
        system_message ="""You are an intelligent Sqlite3 agent. You generate and execute SQL queries to retrieve data based on instructions from the 'Planner'.
        You use the `sqlite_tool` to interact with the database.
        Your response should contain the SQL query and the query results.
        
        """
       
    )
    #sqlite3_agent.register_tool(sqlite3_tools)
    return sqlite3_agent