import asyncio
from pathlib import Path
from database.database_utility import configure_database
from teams.database_team import get_database_team
from langchain.sql_database import SQLDatabase
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult


async def main():

    print(" Execution Started ......")
    dbfilepath = (Path(__file__).parent/"database/sales.db").absolute()
    print('Database Path :',dbfilepath)
    #MYSQL_DB = 'MySQL'
    #SQLITE_DB = 'SQLite' 'localhost:3306', 'root','AmiSam%40123','employees'
    selected_database ='SQLite' 
    database_uri = 'sales.db'
    database_host ='localhost:3306'
    database_user = 'root'
    database_password = 'AmiSam%40123'
    database_name ='employees'

    # user input .. taken from user end .
    database = configure_database(selected_database, database_uri, database_host, database_user, database_password, database_name)

    database_team = get_database_team(database)

    async for message in database_team.run_stream():
        if isinstance(message,TextMessage):
            print('==' * 20)
            print(message.source,' : ',message.content)
        elif isinstance(message,TaskResult):
            print('Stop Reason :', message.stop_reason)     

if __name__ == "__main__":
    asyncio.run(main())
