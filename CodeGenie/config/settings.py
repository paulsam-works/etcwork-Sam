import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.constant import MODEL

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def get_model_client():
    """
    Function to get the OpenAI Chat Completion Client.
    This client will be used to interact with the OpenAI API.
    """
    model_client = OpenAIChatCompletionClient(
        model=MODEL,
        api_key=OPENAI_API_KEY
    )
    return model_client