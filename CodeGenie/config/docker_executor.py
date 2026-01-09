from autogen_ext.code_executors import DockerCommandLineCodeExecutor
from config.constant import WORK_DIR, TIMEOUT


def get_docker_executor():

   """  
   Function to get the Docker Command Line Code Executor.
    This executor will run the code in a Docker container. 
   """

   docker_executor = DockerCommandLineCodeExecutor(
      work_dir = WORK_DIR,
      timeout = TIMEOUT
   )

   return docker_executor