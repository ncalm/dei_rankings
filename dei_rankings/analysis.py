"""
This module provides simplified functionality for quick analysis of rankings data

Functions:
    get_rankings_data: loads data from one or more CSV files in the cwd
"""
import os
import pandas as pd
from dei_rankings import logging_config

logger = logging_config.logger

def get_rankings_data(file_pattern: str = '.csv') -> pd.DataFrame:
    """
    
    Loads data from one or more CSV files in the cwd

    Arguments:
        file_pattern (str) -- optional str which should exist in the file name (e.g. usa)

    Returns:
        A dataframe containing the rankings from one or more files

    """

    # Load Sheet1 from datasets.xlsx file from the root folder
    df_datasets = pd.read_excel(r'..\data\datasets.xlsx', sheet_name='datasets')

    # a list to hold the dataframes from each file
    dfs = []

    for f in os.listdir("..\\data"):
        if f.startswith('r_statista') and (file_pattern in f) and f.endswith('.csv'):

            df = pd.read_csv('..\\data\\' + f)

            # populate the study country and year columns from the filename
            df[['study','country','year']] = [f.split('_')[t] for t in [2,3,4]]

            # remove the .csv suffix and populate a filename column
            df['year'] = df.year.str.replace('.csv', '', regex=True).astype(int)
            df['filename'] = f

            chart_title = df_datasets[df_datasets.filename == 'data\\' + f].chart_title.unique()[0]

            # print(chart_title)

            # get the chart_title column from df_datasets for the row where filename == f
            df['chart_title'] = chart_title

            dfs.append(df)

    # combine the list of dfs into a single df
    df_result = pd.concat(dfs)

    logger.info("Found %s rows in %s files.", len(df_result), len(dfs))

    return df_result

# function get_source_data(country, study, year) to retrieve url from datasets.xlsx
def get_source_data(country: str, study: str, year: int) -> pd.DataFrame:
    """
    Retrieves the source data from datasets.xlsx for a given country, study, and year.

    Arguments:
        country (str) -- the country to retrieve data for
        study (str) -- the study to retrieve data for
        year (int) -- the year to retrieve data for

    Returns:
        A dataframe containing the source data for the given country, study, and year.
    """

    # Load Sheet1 from datasets.xlsx file from the root folder
    df_datasets = pd.read_excel(r'..\data\datasets.xlsx', sheet_name='datasets')

    # filter df_datasets for rows where country, study, and year match the input arguments
    df_result = df_datasets[(df_datasets.country == country) & (df_datasets.study == study) & 
                            (df_datasets.year == year)]

    return df_result
