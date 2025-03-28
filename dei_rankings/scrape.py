"""
This module provides web scraping capabilities to extract rankings from r.statista.com.
"""

from os.path import exists
from typing import List
import traceback
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
# from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import requests
from dei_rankings import logging_config


logger = logging_config.logger
LOAD_WAIT_SECONDS = 10

def get_selenium_driver():
    """
    Initializes and returns a Selenium WebDriver with default settings.
    """
    options = Options()
    options.add_argument("--headless")
    # options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    # options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # driver = webdriver.Chrome(
    #     service=Service(ChromeDriverManager().install()), options=options
    # )
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(LOAD_WAIT_SECONDS)
    return driver

def get_available_rankings(url="https://r.statista.com/en/employers/"):
    """
    Retrieves a list of available ranking URLs from the given source page.
    """
    driver = get_selenium_driver()
    driver.get(url)

    links = driver.find_elements(
        By.XPATH, "//a[contains(@href, '://r.statista.com') and contains(@href, 'employers')]"
    )
    href_list = list(set(
        link.get_attribute("href") for link in links if 'claim' not in link.get_attribute('href')
    ))
    validated_links = [link for link in href_list if is_valid_ranking_page(driver, link)]
    driver.quit()
    return validated_links

def is_valid_ranking_page(driver, link):
    """
    Checks if the given ranking page contains a valid table with a 'Rank' column.
    """
    driver.get(link)
    try:
        driver.find_element(By.XPATH, "//th[text()='Rank']")
        return True
    except NoSuchElementException:
        return False

def get_rows_from_url(url: str) -> List[List]:
    """
    Extracts ranking data from the given URL and returns it as a list of rows.
    """
    driver = get_selenium_driver()
    driver.get(url)
    logger.info("Loading %s", url)
    try:
        select = Select(WebDriverWait(driver, LOAD_WAIT_SECONDS).until(
            EC.presence_of_element_located((By.NAME, "statistaEmployerRankingTable_length"))
        ))
        select.select_by_value('100')
        logger.info("Selecting 100 rows per page")
    except NoSuchElementException:
        logger.error("Page-size drop-down not found")
        return None

    rows = []
    # for page in range(1, 6):  # Max 5 pages
    #     logger.info("Waiting for page to load")
    #     pagination_link = driver.find_elements(By.CSS_SELECTOR, f"a[data-dt-idx='{page}']")
    #     logger.info("Pagination link: %s", pagination_link)
    #     if not pagination_link:
    #         logger.info("No more pages available. Stopping.")
    #         break

    #     logger.info("Processing page %d", page)
    #     pagination_link[0].click()  # Click the page link
        
    #     WebDriverWait(driver, 5).until(
    #         EC.presence_of_element_located((By.TAG_NAME, 'table'))
    #     )
    #     rows.extend(parse_table_html(driver.page_source))
    for page in range(1, 6):  # Max 5 pages
        logger.info("Processing page %d", page)
        pagination_link = driver.find_elements(By.CSS_SELECTOR, f"a[data-dt-idx='{page}']")
        if not pagination_link:
            logger.info("No more pages available. Stopping.")
            break
        driver.execute_script(
            f"document.querySelector('a[data-dt-idx=\"{page}\"]').click()"
        )
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'table'))
        )
        rows.extend(parse_table_html(driver.page_source))


        # if page == 2:
        #     print(rows)

    driver.quit()
    return rows

def parse_table_html(html_content):
    """
    Parses an HTML table and extracts data into a list of rows.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", id="statistaEmployerRankingTable") or \
            soup.find("table", id="statistaRankingTableLocalRanking")
    return [
        [td.text.strip() for td in tr.find_all("td")] for tr in table.find_all("tr")[1:]
    ] if table else []

def clean_rows(rows: List) -> pd.DataFrame:
    """
    Cleans extracted ranking data into a structured pandas DataFrame.
    """
    logger.info("Cleaning rows")
    logger.info("Columns: %s", rows[0])
    # log the number of columns in rows
    for row in rows:
        if len(row) != len(rows[0]):
            logger.info("Row length: %d on %s", len(row), row)
    df = pd.DataFrame(rows, columns=[
        'rank', 'company', 'employees', 'score', 'location', 'industry'
    ])
    # originally developed pattern stopped working in 2025
    # pattern = r'^(.*?)(?:\n(.*?))?$'
    pattern = r"(?s)^(.*?)\n.*?Founded[^\d]*([\d]+)?"
    df[['company', 'founded']] = df['company'].str.extract(pattern)
    # pattern = r'^(.*?)(?:\n(.*?))?$'
    pattern = r"(?s)^(.*?)\n.*?CEO[\n](.+)$"
    df[['score', 'ceo']] = df['score'].str.extract(pattern)
    # pattern = r'^(.*?)(?:Headquarters\n(.*?))?$'
    pattern = r'(?s)^(.*?)\n.*?(?:Headquarters\n(.*?))?$'
    df[['state', 'hq']] = df['location'].str.extract(pattern)
    df['industry'] = df['industry'].str.split('\n', expand=True)[0]
    df['employees'] = df['employees'].str.split('\n', expand=True)[1]
    df.drop(columns=['location'], inplace=True, errors='ignore')
    logger.info("Finished cleaning rows")
    return df[['rank', 'company', 'founded', 'employees',
               'score', 'ceo', 'state', 'hq', 'industry']]

def get_etag(url):
    """
    Retrieves the ETag header from the given webpage to check for updates.
    """
    try:
        response = requests.head(url, timeout=5)
        return response.headers.get("ETag")
    except requests.RequestException:
        return None

def safe_execute(func, *args, **kwargs):
    """
    Wraps a function call with exception handling to prevent crashes.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("Error in function %s: %s\n%s", func.__name__, str(e), traceback.format_exc())
        return None

def to_csv(url, filename, force_refresh=False):
    """
    Retrieves, cleans, and saves ranking data to a CSV file if updates are detected.
    """
    # etag = get_etag(url)
    if not exists(filename) or force_refresh is True:
        logger.info("Downloading %s", filename)
        rows = safe_execute(get_rows_from_url, url)
    else:
        logger.info("File already exists for %s", filename)
        return

    # rows = safe_execute(get_rows_from_url, url)
    if rows:
        df = clean_rows(rows)
        df.to_csv(filename, index=False)
