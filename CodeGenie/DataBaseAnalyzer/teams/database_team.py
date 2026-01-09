from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from config.settings import get_model_client
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.constant import MAX_TURNS
from agents.user_agent import get_user_agent
from agents.db_planner_agent import get_db_planner_agent
from agents.mysql_agent import get_mysql_agent
from agents.sqlite_agent import get_sqlite_agent


def get_database_team(database):

    # setting termination conditions
    text_mention_termination = TextMentionTermination("TERMINATE")
    max_message_termination = MaxMessageTermination(MAX_TURNS)
    combined_termination = text_mention_termination | max_message_termination

    # setting up the agents 
    user_agent = get_user_agent()
    db_planner_agent = get_db_planner_agent()
    mysql_agent = get_mysql_agent()
    sqlite_agent = get_sqlite_agent(database)

    # prompt for selector 
    selector_prompt = """ 
    Select an agent to perform the task.

    {roles}
    
    Current conversation history.
    {history} 
    
    Read the above conversation, then select an agent from the {participants} to perform the next task.
    Make sure User Agent will ask the question first. And then db_planner_agent will take the task.
    db_planner_agent then break the task into subtask and publish the detail plan for execution. 
    DB plannar agent then do the planning and assign the task to the other agents based on task.
    Only select one agent at one time.
    
    """

    selector_team = SelectorGroupChat(
        name = "Database_Analyzer_Team",
        participants =[user_agent, db_planner_agent, mysql_agent, sqlite_agent],
        model_client = get_model_client(),
        termination_condition = combined_termination,
        allow_repeated_speaker= True
    )
    return selector_team


