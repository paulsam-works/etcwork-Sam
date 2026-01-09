from autogen_agentchat.agents import UserProxyAgent

def get_user_agent():
    user_agent = UserProxyAgent(
        name = "User_Agent",
        description = " An agent that represents the user and forwards the user's queries to other agents in the team.",
        input_func= input
    )
    return user_agent
