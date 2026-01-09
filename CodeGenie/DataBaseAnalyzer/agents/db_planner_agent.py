from autogen_agentchat.agents import AssistantAgent
from config.settings import get_model_client

# get the model client
model_client = get_model_client()


def get_db_planner_agent() -> AssistantAgent:
    db_planner_agent = AssistantAgent(
        name = "Db_Planner_Agent",
        model_client = model_client,
        description = "An agent that creates a plan to analyze the database and get insights from it.",
        system_message="""You are an Intelligent Database Planner. You receive requests from a user and formulate a plan of action.
        From the user's request, user will mention that they want to analyze a database and give a query request.
        From the user's request you have to create a step by step execution plan to solve the user's request by analyzing the mentioned database
        If the request involves querying a database, your plan should involve using the 'Code_Executor_Agent' to generate SQL code and to execute the code.
        If the request involves analyzing the results, your plan should involve a step to 'summarize_results'.
        Your role is to lay out the high-level steps, not to write code yourself.
        Example plan:
        1. Generate and execute SQL query to retrieve data.
        2. Analyze the query results.
        3. Summarize the findings for the user.
    """
    )
    return db_planner_agent