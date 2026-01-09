from autogen_agentchat.agents import CodeExecutorAgent
from config.docker_executor import get_docker_executor


def get_code_executor_agent():

    """

    Function to get CodeExecutor Agent.
    This agent is responsible for executing code snippet.StopAsyncIteration.
    This agent will work with ProblemSolverAgent to execute the code. 
    
    """
    docker = get_docker_executor()
    code_executor_agent = CodeExecutorAgent(
        name = "CodeExecutorAgent",
        code_executor = docker
    )

    return code_executor_agent, docker