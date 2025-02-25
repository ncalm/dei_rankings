"""This module provides web scraping capabilities of rankings
from r.statista.com.

Functions:
    read_file - read a file and return its contents as a string
    write_file - write a string to a file
"""

from os.path import exists
# from webdriver_manager.chrome import ChromeDriverManager
from typing import List
from datetime import datetime
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
import openpyxl
# from rankings
import logging_config

logger = logging_config.logger

LOAD_WAIT_SECONDS = 10


def get_core_url_part(url: str) -> str:
    """Extracts the identifying part of a URL. E.g. In:
    http://r.statista.com/best-employers-singapore-2022/

    The identifying part is 'best-employers-singapore-2022'

    Arguments:
        url (str) -- any url that we suspect contains ranking data

    Returns:
        The part of the URL that identifies the content

    """
    parts = [part for part in url.split('/') if part != '']
    # print(parts)

    # If the last part is 'ranking', then the second to last part is the identifier
    if parts[-1] == 'ranking':
        core_part = parts[-2]
    else:
        # It's a non-standard URL, look for the part based on keywords
        parts = (part for part in parts if 'best' in part or 'employers-' in part)
        try:
            core_part = next(parts)
        except StopIteration as exc:
            error_message = f'Error: No matching URL part found in {url}'
            raise ValueError(error_message) from exc
        try:
            next(parts)
            raise ValueError(
                f'Error: More than one matching URL part found in {url}')
        except StopIteration:
            pass

    return core_part


def standardize_url(url: str) -> str:
    """Some URLs are of a non-standard format. E.g.
    http://r.statista.com/best-employers-singapore-2022/

    Such URLs are reformatted to meet the actual expected location. E.g.
    http://r.statista.com/employers/best-employers-singapore-2022/ranking/

    Arguments:
        url (str) -- any url that we suspect contains ranking data

    Returns:
        A reformatted URL that includes the /employers/ sub-directory and ends 
        with /rankings/

    """

    if url.endswith('/ranking/'):
        return url
    else:
        part = get_core_url_part(url)
        return f'http://r.statista.com/employers/{part}/ranking/'


def get_available_rankings(url: str = "https://r.statista.com/en/employers/"):
    """Gets a list of URLs from a source page

    Arguments:
        url (str) -- a url pointing to a page that contains multiple links
        to rankings pages

    Returns:
        A list of URLs retrieved from the page

    """

    # set up the Selenium web driver with headless mode
    options = Options()
    options.add_argument('--headless')

    # if the chromedriver isn't found in the cache, download and install it

    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver = webdriver.Chrome(options=options)

    # load the page using Selenium
    driver.get(url)
    # driver.implicitly_wait(LOAD_WAIT_SECONDS)

    # Find the list of links (some are malformed and don't end with \rankings\)
    links = driver.find_elements(
        By.XPATH,
        "//a[contains(@href, '://r.statista.com') \
            and contains(@href, 'employers')]")

    # Get the URL of each link. But not the root page... duh
    # and not the page that links to a claim form for the company
    href_list = [
        standardize_url(link.get_attribute("href"))
        # link.get_attribute("href")
        for link in links
        if link.get_attribute('href') != url
        and 'claim' not in link.get_attribute('href')
    ]

    # Remove duplicates
    href_list = list(set(href_list))

    # for each link in href_list, open the link and look for a table with a Rank column
    # if the Rank column is not found, discard the link
    # Note: This adds some execution time but is important for weeding out links that
    # don't contain the data we're looking for
    for link in href_list:
        driver.get(link)
        try:
            driver.find_element(By.XPATH, "//th[text()='Rank']")
        except NoSuchElementException:
            href_list.remove(link)

    # close the driver
    driver.quit()

    return href_list


def get_rows_from_url(url: str) -> List[List]:
    """Retrieves company ranking data from a statista R url

    Arguments:
        url (str) -- a url pointing to a 'ranking' page

    Returns:
        A list of rows retrieved from the url

    """

    # Set up desired capabilities
    capabilities = DesiredCapabilities.CHROME
    capabilities['loggingPrefs'] = {'browser': 'SEVERE'}

    # set up the Selenium web driver with headless mode
    options = Options()
    options.add_argument("--headless")

    # Set logging level to suppress most console messages
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # if the chromedriver isn't found in the cache, download and install it
    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver = webdriver.Chrome(options=options)

    # load the page using Selenium
    driver.get(url)

    # wait for up to LOAD_WAIT_SECONDS seconds before throwing an exception if the element
    # can't be found
    driver.implicitly_wait(LOAD_WAIT_SECONDS)

    # Find the page element for the 'show this many rows' dropdown
    try:
        select_element = driver.find_element(
            By.NAME, "statistaEmployerRankingTable_length")
    except NoSuchElementException as e:
        logger.error('Couldn\'t find page-size drop-down: %s', type(e))
        return None

    select = Select(select_element)

    # Select the option with the value of "100"
    select.select_by_value('100')

    # wait for the table to load
    driver.implicitly_wait(LOAD_WAIT_SECONDS)

    # Find the total number of results and number of rows per page
    # find the list of buttons for switching pages
    pagination_element = driver.find_element(By.CLASS_NAME, 'pagination')

    # find the right-most button that isn't the "next" button
    li_elements = pagination_element.find_elements(By.TAG_NAME, 'li')

    # for li in li_elements:
    #     print(li.get_attribute('class'), li.text)

    # the right-most (bottom) list item should be the 'next' button, which has a label '>'
    # since during this automation, the first page is selected by default
    # we don't need to worry about the class being 'paginate_button page-item next disabled'
    if li_elements[-1].get_attribute('class') in ['paginate_button page-item next',
                                                  'paginate_button page-item next disabled']:
        max_page_element = li_elements[-2]
    else:
        max_page_element = li_elements[-1]

    # get the link from the selected element
    max_page_link = max_page_element.find_element(By.TAG_NAME, 'a')

    # get the text from the link and convert it to an integer
    max_page_number = int(max_page_link.text)

    # function to be called each time a new 100 rows is displayed
    def get_rows(html_content, rows):

        # create a BeautifulSoup object to parse the HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # find the table element using the ID selector
        table = soup.find("table", id="statistaEmployerRankingTable")

        if table is None:
            table = soup.find("table", id="statistaRankingTableLocalRanking")

        # extract the table rows
        for tr in table.find_all("tr")[1:]:
            row = []
            for td in tr.find_all("td"):
                row.append(td.text.strip())
            rows.append(row)

        return rows

    rows = []

    # since there are 500 companies in the list, and we've changed the "view" selector to
    # 100, we need to loop through 5 pages to get all the data
    for page in range(1, max_page_number + 1):

        try:
            # Click on the page link
            page_link = driver.find_element(By.XPATH, f'//a[text()="{page}"]')
            driver.execute_script("arguments[0].click();", page_link)

            # wait for the table to load
            driver.implicitly_wait(5)

            # extract the page source and close the driver
            html_content = driver.page_source

            rows = get_rows(html_content, rows)
        except NoSuchElementException:
            pass

    return rows


def clean_rows(rows: List) -> pd.DataFrame:
    """Applies cleaning steps to rows retrieved from statista R

    Arguments:
        rows (list) -- A list of rows created by get_rows_from_url

    Returns:
        A dataframe containing the rows

    """

    df = pd.DataFrame(
        rows, columns=['rank', 'company', 'employees', 'score', 'location', 'industry'])

    # TODO: handle edge cases where there is no 'founded' or 'ceo' column
    df[['company', 'founded']] = df['company'].str.split(
        '\n', expand=True).iloc[:, [0, 3]]

    df[['score', 'ceo']] = df['score'].str.split(
        '\n', expand=True).iloc[:, [0, 3]]

    df[['state', 'hq']] = df['location'].str.split(
        'Headquarters\n', expand=True).apply(lambda x: x.str.strip())

    df['industry'] = df['industry'].str.split('\n', expand=True)[0]

    df['employees'] = df['employees'].str.split('\n', expand=True)[1]

    # drop the original 'score' and 'location' columns
    df.drop(['location'], axis=1, inplace=True)

    # reorder the columns
    df = df[['rank', 'company', 'founded', 'employees',
             'score', 'ceo', 'state', 'hq', 'industry']]

    return df


def to_csv(url, filename, force_refresh=False):
    """Returns tabulated data from url, cleans it and saves it to filename

    Arguments:
        url (str) -- The url of a statista R page as defined in datasets.xlsx
        filename (str) -- The name of the csv file to save the data to

    Returns:
        None

    """

    # Check if file already exists
    if not exists(filename) or force_refresh is True:

        rows = get_rows_from_url(url)

        if not rows:
            logger.warning("No rows were returned from %s or saved to %s", url, filename)
        else:
            logger.info("Scraping data from %s", url)
            df = clean_rows(rows)
            df.to_csv(filename, index=False)
            logger.info("%s rows from %s written to '%s'", len(rows), url, filename)

    else:
        logger.info("%s already exists. File was not refreshed.", filename)


def predict_country_study_year(core_part, country_map, study_map):
    """Tokenizes the core part of a url and attempts to predict the country, study and year.
    
    Arguments:
        core_part (str) -- the part of the url that comes after the domain name and before 
            the ranking. Provided by get_core_url_part.
        country_map (dict) -- maps potential country tokens to country names
            retrieved from datasets.xlsx sheet 'country_map'
        study_map (dict) -- maps potential study tokens to study names
            retrieved from datasets.xlsx sheet 'study_map'

    Returns:
        tuple -- (country, study, year) if all three can be predicted, else
        None
    
    """

    logger.info('Attempting to predict variables for core_part: %s', core_part)

    tokens = core_part.split('-')
    logger.info('Tokens: %s', tokens)

    # TODO: implement translation of tokens to English
    exclusions = ["best", "beste", "employers", "arbeitgeber", "the", "feur"]

    # remove exclusions from tokens
    tokens = [token for token in tokens if token not in exclusions]

    logger.info('Tokens without exclusions: %s', tokens)


    # if one of the tokens is a four-digit integer, it's probably the year
    for token in tokens:
        if len(token) == 4 and token.isdigit():
            predicted_year = int(token)
            tokens.remove(token)
            break
    else:
        logger.warning('Unable to predict year for %s', core_part)
        return None

    logger.info('Predicted year: %s', predicted_year)

    # if one of the tokens is a country name that also appears in the table, it's probably
    # the country
    for token in tokens:
        if token in country_map:
            predicted_country = country_map[token]
            tokens.remove(token)
            # else if the token ends in an s, remove it and try again
        elif token.endswith('s'):
            token = token[:-1]
            if token in country_map:
                predicted_country = country_map[token]
                break
        else:
            logger.warning('Unable to predict country for %s', core_part)
            return None

    logger.info('Predicted country: %s', predicted_country)

    # if one of the tokens is a study name that also appears in the table, it's probably the study
    if len(tokens) == 0:
        predicted_study = 'best'
    else:
        for token in tokens:
            if token in study_map:
                predicted_study = study_map[token]
                tokens.remove(token)
                break
        else:
            logger.warning('Unable to predict study for %s', core_part)
            return None

    logger.info('Predicted study: %s', predicted_study)

    # if we have a year, country and study, we're done
    if predicted_year and predicted_country and predicted_study:
        return (predicted_country, predicted_study, predicted_year)
    else:
        logger.warning('Unable to predict country, study and year for %s', core_part)
        return None



def add_new_dataset(data_dict: dict):
    """Adds a new row to the datasets sheet in datasets.xlsx
    
    Arguments:
        data_dict (dict) -- the country, study, year and url as keys of a dictionary
            the dict values are the values to be written to the row

    Returns:
        list representing the new row. Includes datetime the row was added
    
    
    """

    filepath = r'..\data\datasets.xlsx'

    # Load the workbook and select the 'datasets' sheet
    workbook = openpyxl.load_workbook(filepath)
    sheet = workbook['datasets']
    table = sheet.tables['datasets']

    data_list = []
    for col in table.tableColumns:
        formula = col.calculatedColumnFormula
        if col.name in data_dict:
            data_list.append(data_dict[col.name])
        elif col.name == 'added':
            data_list.append(datetime.now())
        elif col.name == 'link_valid':
            data_list.append(1)
        elif not formula is None:
            data_list.append('=' + formula.text)
        else:
            data_list.append(None)

    sheet.append(data_list)
    logger.info('New row added to dataset repository: %s', data_list)

    # expand table reference
    tl, br = table.ref.split(':')
    alpha = ''.join(c for c in br if c.isalpha())
    table.ref = f'{tl}:{alpha}{sheet.max_row}'

    # Save the workbook
    workbook.save(filepath)

    return data_list
