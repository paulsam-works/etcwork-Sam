from autogen_agentchat.agents import AssistantAgent
from config.settings import get_model_client

# get the model client
model_client = get_model_client()


def get_problem_solver_agent():
    
    """ 
    Function to get Problem Solver Agent.
    This agent is responsible for solving the DSA problems.
    It will work with code executor agent to solve the problem. 
    
    """

    problem_solver_agent = AssistantAgent(
        name = "DSA_Problem_Solver_Agent",
        description="An agent that solves DSA problems.",
        model_client= model_client,
        system_message = """ 
        You are a highly intelligent problem solver agent that is an expert in solving DSA problems.
        You will be working with code executor agent to execute the code.
        You will be given a task and you have to solve the problem.
        At the begining of your response you have to specify your plan to solve the task.
        Then you should give the code in a code block. (Python)
        You should write code in a code block at a time and then pass it to code executor agent to execute the code.
        Make sure that we have atleast 3 test cases for the code you write.
        Once code is executed and if the same has beeen executed successfully, you have the results.
        You should explain the code executor result.

        Once the code explanation is done, you should ask the code executor agent to save the code in file.
        like this:
        ```python

        code = '''
            print("Hello World")
        '''

        with open('solution.py', 'w') as f:
            f.write(code)
            print("code saved successfully in solution.py")
        ```

        You should send the above code block to the code executor agent so that it can save the code in a file. Make sure to provide the code in a block.
        In the end once code is executed successfully, you have to say "STOP" to stop the conversation. 
        
        """

    )

    return problem_solver_agent