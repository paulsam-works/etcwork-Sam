import os
import sqlite3
from pathlib import Path
import sqlite3
from config.constant import MYSQL_DB, SQLITE_DB, ORACLE_DB, PYGRES_DB
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits import SQLDatabaseToolkit



def configure_database(selected_database, database_uri, database_host = None, database_user = None, database_password = None, database_name = None):
    """ 
    Configures and returns a SQLDatabase instance based on the provided database URI.
    
    Args:
        database_uri (str): The URI of the database. Supported formats:
                            - SQLite: "sqlite:///path_to_db"
                            - MySQL: "mysql+mysqlconnector://user:password@host/dbname"
        database_host (str, optional): Hostname for MySQL databases.
        database_user (str, optional): Username for MySQL databases.
        database_password (str, optional): Password for MySQL databases.            
        database_name (str, optional): Database name for MySQL databases.
    
    Returns:
        SQLDatabase: An instance of SQLDatabase connected to the specified database. 
    
        
    """

    if selected_database == MYSQL_DB:
        """
        Checks if param1 and param2 are not None or empty.
        Raises a ValueError if either is invalid.
        """
        if not database_host or not database_user or not database_password or not database_name:
            raise ValueError("For MySQL, database_host, database_user, database_password, and database_name cannot be None or empty.")
        
        mysql_database = SQLDatabase(create_engine(f"mysql+mysqlconnector://{database_user}:{database_password}@{database_host}/{database_name}"))
        print('MySQL employee data base successfully connected .....')
        return mysql_database
    
    elif selected_database == SQLITE_DB:
        try:
            dbfilepath = (Path(__file__).parent/"sales.db").absolute()
            print(" Sqlite3 Database file path::",dbfilepath)
            creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
            dbase = SQLDatabase(create_engine("sqlite://",creator=creator))
            print('Sqlite3 sales data base successfully connected .....')
        except sqlite3.Error as e:
            print(f"Error connecting the sqlite3 database : {e}")
            dbase = None 

        return dbase
    