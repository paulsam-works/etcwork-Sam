from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import TaskResult
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
import os


load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

async def team_config(news_topics ="Latest Drug Devlopement Updates"):
    model_client = OpenAIChatCompletionClient(model = 'gpt-4o', api_key = OPENAI_API_KEY)
    
    news_topics ="Latest Drug Devlopement Updates"
    
    # Defining our Agents
    news_anchor = AssistantAgent(
        name = "news_anchor",
        model_client = model_client,
        description = f"An AI Agent that finds the key summarized updates for {news_topics} for new drugs",
        system_message =f""" You are a professional News Anchor that finds the key for {news_topics} for new drug devlopements 
        summarized updates for {news_topics} for new drug devlopements in Global Pharma Industry.
        Your Job is to provides latest updates in Pharma Research Industry based on  asked question.
        Take minimum 3 question and answer them based on given query. After providing answer to 3 questions, say 'TERMINATE' at the end.
       """
    )
    
    # User Agent
    user_agent = UserProxyAgent(
        name = "user_agent",
        description = f"An agent that stimulates user for asking questions on {news_topics}."
    )

    # Market Analyzer
    market_analyzer = AssistantAgent(
        name = "market_analyzer",
        model_client = model_client,
        system_message =f"""  You are a Pharma Drug Marketing Specialist who can able to analyze any new drug that comes into market.
        Also make a detail study on this product feature, quality, cost, trial details, success factor. Also make 
        a competitive study with other similar product in market and provide a detail analysis. Please keep this analysis 
        in 400 words.
    """
    )

    terminate_condition = TextMentionTermination(text="TERMINATE")

    team = RoundRobinGroupChat(
        participants=[user_agent,news_anchor,market_analyzer],
        termination_condition=terminate_condition,
        max_turns=3
    )
    return team

async def news_session(team):
# running the session
    async for message in team.run_stream(task='Start the news session with user question.'):
        if isinstance(message,TaskResult):
            message = f'News Session completed with {message.stop_reason}'
            yield message
        else:
            message = f'{message.source}: {message.content}'
            yield message

async def main():
    news_topics ="Latest Drug Devlopement Updates"
    team = await team_config(news_topics)

    async for message in news_session(team):
        print('-'*70)
        print((message))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())





