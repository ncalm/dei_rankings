"""This module provides functions to interact with a SQLite database."""
import sqlite3
from pathlib import Path
import os
import pandas as pd

SQLITE_PATH = os.path.abspath("../data/datasets.db")
DATA_FOLDER_PATH = Path("../data")


def sqldml(cmd, params=None):
    """
    Executes a SQL DML (Data Manipulation Language) command on the SQLite database.
    This includes INSERT, UPDATE, and DELETE operations.

    Arguments:
        cmd (str): The SQL command to execute.
        params (tuple or list, optional): The parameters to safely bind to the SQL command.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        if params:
            conn.execute(cmd, params)  # Use parameterized query
        else:
            conn.execute(cmd)
        conn.commit()
        return True
    except sqlite3.OperationalError as e:
        print(f"Operational Error: {e}")
        return False
    except sqlite3.DatabaseError as e:
        print(f"Database Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def sqlddl(cmd):
    """Executes a DDL command on the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute(cmd)
        conn.commit()
        return True
    except sqlite3.OperationalError as e:
        print(f"Operational Error: {e}")
        return False
    except sqlite3.DatabaseError as e:
        print(f"Database Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def sqlselect(cmd):
    """Executes a SELECT command on the SQLite database and returns the result as a DataFrame."""
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        df = pd.read_sql_query(cmd, conn)
        return df
    except sqlite3.OperationalError as e:
        print(f"SQL Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def sqllookup(lookup_table, singular):
    """Creates a lookup table for a specified column in the datasets table."""
    try:
        # Drop the lookup table if it exists
        query = f"DROP TABLE IF EXISTS {lookup_table}"
        if not sqlddl(query):
            raise Exception(f"Failed to drop table {lookup_table}")

        # Create the lookup table
        query = f"CREATE TABLE {lookup_table} ({singular}_id INTEGER PRIMARY KEY, {singular} TEXT)"
        if not sqlddl(query):
            raise Exception(f"Failed to create table {lookup_table}")

        # Populate the lookup table with distinct values
        query = f"""
        INSERT INTO {lookup_table} ({singular})
        SELECT DISTINCT {singular}
        FROM datasets
        WHERE {singular} IS NOT NULL AND {singular} != ''
        """
        if not sqlddl(query):
            raise Exception(f"Failed to populate table {lookup_table}")

        # Add a new column to the datasets table if it doesn't exist
        query = f"ALTER TABLE datasets ADD COLUMN {singular}_id INTEGER"
        sqlddl(query)  # This may fail if the column already exists, but we can ignore it

        # Set the new column to NULL
        query = f"UPDATE datasets SET {singular}_id = NULL"
        if not sqlddl(query):
            raise Exception(f"Failed to initialize {singular}_id column in datasets table")

        # Update the new column with the corresponding ID from the lookup table
        query = f"""
        UPDATE datasets
        SET {singular}_id = (
            SELECT {singular}_id
            FROM {lookup_table}
            WHERE {lookup_table}.{singular} = datasets.{singular}
        )
        """
        if not sqlddl(query):
            raise Exception(f"Failed to update {singular}_id column in datasets table")

        print(f"Lookup table {lookup_table} created and linked successfully.")
    except Exception as e:
        print(f"Error in sqllookup: {e}")

def refresh_dataframes():
    """
    Refreshes dataframes by querying specified tables from the SQLite database.
    Returns a dictionary of table names and their corresponding dataframes.
    """
    dataframes = {}

    table_ids = {
        "datasets": "dataset_id",
        "countries": "country_id",
        "studies": "study_id",
        "rankings_raw": "rankings_raw_id",
    }

    tables = list(table_ids.keys())

    for table in tables:
        try:
            query = f"SELECT * FROM {table}"
            df = sqlselect(query)
            if df is not None:
                dataframes[table] = df.set_index(table_ids[table])
                print(f"Successfully retrieved table '{table}' with {len(df)} rows.")
            else:
                print(f"Warning: Table '{table}' could not be retrieved.")
        except Exception as e:
            print(f"Error while getting table '{table}': {e}")

    if not dataframes:
        print("No tables were successfully retrieved.")
    else:
        print(f"Retrieved {len(dataframes)} tables successfully.")

    return dataframes


# function to insert a row to either study_map or country_map
def insert_new_mapping(data_dict: dict, table_name: str):
    """
    Inserts a new row into either the study_map or country_map table in the SQLite database.

    Arguments:
        data_dict (dict): A dictionary containing the keys 'token' and 'name'

    Uses sqldml to execute the prepared insert statement.

    Returns:
        bool: True if the insertion was successful, False otherwise.
    """
    if table_name not in ['study_map', 'country_map']:
        print(f"Error: Invalid table name '{table_name}'. Must be 'study_map' or 'country_map'.")
        return False

    # Ensure data_dict contains the required keys
    if 'token' not in data_dict or 'name' not in data_dict:
        print("Error: 'token' and 'name' keys are required in data_dict.")
        return False

    # Prepare the SQL query
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join('?' * len(data_dict))
    sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'

    # Prepare the values
    values = tuple(data_dict.values())

    # Execute the SQL command to insert the new row
    return sqldml(sql, values)
