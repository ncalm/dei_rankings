"""
This script is used to scrape the data from the rankings page and save it to a file.
"""
import sys
import pandas as pd
import dei_rankings.scrape as ws
import dei_rankings.analysis as ra
import dei_rankings.utils as utils

# sys.path.append('..')

DATASETS_PATH = '.\\data\\datasets.xlsx'

# Open the Excel file once and create an ExcelFile object
try:
    excel_file = pd.ExcelFile(DATASETS_PATH)
except FileNotFoundError:
    ws.logger.error("File not found: %s", DATASETS_PATH)
    sys.exit(1)

tables = ['datasets', 'study_map', 'country_map']

# check that each of the tables exists in the file
for table in tables:
    if table not in excel_file.sheet_names:
        ws.logger.error("Sheet '%s' not found in %s", table, DATASETS_PATH)
        sys.exit(1)

# load the datasets.xlsx file from the root folder, being sure to include the data types
dtypes = {'country': str, 'study': str, 'year': str, 'url': str, 'filename': str,
          'link_valid': int, 'added': 'datetime64[ns]', 'chart_title': str, 
          'comment': str}

# try to read the datasets sheet using the dtypes given
try:
    datasets = pd.read_excel(excel_file, sheet_name='datasets', dtype=dtypes)
except ValueError:
    ws.logger.error("Error reading %s Check the data types.", DATASETS_PATH)
    sys.exit(1)

# a token map is a translation table of URL tokens to standardized names used in the project
token_maps = tables.copy()
token_maps.remove('datasets')

# check that each of the token maps exists in the file
for token_map in token_maps:
    if token_map not in pd.ExcelFile(DATASETS_PATH).sheet_names:
        ws.logger.error("Sheet '%s' not found in %s", token_map, DATASETS_PATH)
        sys.exit(1)

# build a dict of table_name: df by looping through the table_names list
tables = {table_name: pd.read_excel(excel_file, sheet_name=table_name)
          for table_name in token_maps}

def get_token_map(table_name):
    """Return a dict of URL tokens to standardized names from the token_maps dict."""
    # print(tables[table_name].columns)
    return dict(zip(tables[table_name].token, tables[table_name].name))

study_map = get_token_map('study_map')
country_map = get_token_map('country_map')



# get the links from the rankings page (somewhat slow)
links = ws.get_available_rankings()

# the core part of the URL for each dataset
core_parts = datasets.url.apply(utils.get_core_url_part)

# check if the available URL retrieved is already in the file or not
output = {link: (core_parts == utils.get_core_url_part(link)).any() for link in links}

# return the links that are not in the file
new_urls = {k: v for k, v in output.items() if not v}

# loop through the new URLs and add them to the datasets file
if new_urls:
    for url in new_urls:
        core_part = utils.get_core_url_part(url)
        result = utils.predict_country_study_year(core_part=core_part,
                                            country_map=country_map,
                                            study_map=study_map)

        data_dict = dict(zip(['country', 'study', 'year'], result))
        data_dict['url'] = url
        new_row = utils.add_new_dataset(data_dict=data_dict)
else:
    ws.logger.info("There were no new urls to add to the datasets file.")
    sys.exit(0)


# loop through the datasets and scrape the data
for index, row in datasets.loc[datasets.link_valid == 1].iterrows():
    url = row['url']
    filename = '..\\' + row['filename']

    # scrape from, save to, refresh file if exists?
    ws.to_csv(url=url, filename=filename)

# load the data
df_filedata = ra.get_rankings_data()
df_filedata.to_json('..\\data\\data.json', orient='records')

ws.logger.info("Finished writing data.json")
sys.exit(0)
