"""
This file focuses on amazon to perform data extraction and manipulation before
all data is pooled together into one single repository
"""
############################################################################################
import re
from time import sleep
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from commonFunctions import clean_data, emulate_browser, clean_dict, clean_name

############################################################################################
def amazon_scrape(browser, search_query, amazon_link):
    """This function scrapes all the search results from our query"""

    # Open amazon.co.uk
    browser.get(amazon_link)

    try:
        # If a cookie pop-up appear click accept
        accept_cookie = browser.find_element(
            By.CSS_SELECTOR, "input[id='sp-cc-accept']"
        )
        accept_cookie.click()

    except NoSuchElementException:
        print("No Cookie Pop-up")

    # Find the search bar
    search = browser.find_element(By.CSS_SELECTOR, "input[id='twotabsearchtextbox']")
    search.click()
    sleep(1)

    # Enter the search query into the search bar
    search.send_keys(search_query)
    search.send_keys(Keys.ENTER)
    sleep(2)

    # Return the number of pages with results
    pages = pagination(browser)

    # Create an empty dictionary
    amazon_results_dict = {}

    # Loop through the pages of results
    for i in range(1, (int(pages) + 1)):
        # Each page returns a dictionary of result data
        results_dict = search_results(browser, amazon_link)
        sleep(1)

        try:
            # Click the next page button until we reach the number of pages
            next_button = browser.find_element(
                By.CSS_SELECTOR,
                "a[aria-label='Go to next page, page {}']".format(i + 1),
            )
            next_button.click()
            sleep(2)

        except NoSuchElementException:
            print("End of pages")

        # Populate our dictionary with each page of result data as we loop
        amazon_results_dict.update(results_dict)

    return amazon_results_dict


############################################################################################
def pagination(browser):
    """This function gathers the page data"""

    # Here we return the element which encapsulates the pagination bar
    pages = browser.find_element(By.CSS_SELECTOR, "span[class='s-pagination-strip']")

    # The page number with the last results is found here
    last_page = pages.find_element(
        By.CSS_SELECTOR, "span[class='s-pagination-item s-pagination-disabled']"
    ).get_attribute("innerHTML")

    return last_page


############################################################################################
def search_results(browser, amazon_link):
    """This function extracts each page worth of relevant results
    with some added filtering"""

    results_dict = {}

    # Results is a list of all the result elements on the page
    results = browser.find_elements(
        By.CSS_SELECTOR, "div[data-component-type='s-search-result']"
    )

    # Looping through the list we look for the description part of the result
    for i in results:
        result_data = i.find_element(
            By.CSS_SELECTOR,
            "div[class='a-section a-spacing-none a-spacing-top-small s-title-instructions-style']",
        )

        exclusive = exclusive_data(i)

        try:
            # Sponsored items may not be relevant so we look for those and...
            result_data.find_element(
                By.CSS_SELECTOR, "div[class='a-row a-spacing-micro']"
            )

        except NoSuchElementException:
            # ...Gather data on all items that are not sponsored

            # Product name
            item = result_data.get_attribute("innerHTML")
            name = result_data.text

            # Link to product
            product_link = re.findall(r'href="(.*?)>', item)
            clean_link = clean_data(product_link)
            final_link = amazon_link + clean_link

            # Barcode information
            ASIN = re.findall(r"dp/(.*?)/ref=", clean_link)
            clean_barcode = clean_data(ASIN)

            exclusivity = "No"
            # Exclusive information
            if exclusive == clean_barcode:
                exclusivity = "Yes"

            # Review data gatherer
            review_data(i, results_dict, clean_barcode, final_link, name, exclusivity)

    return results_dict


############################################################################################
def exclusive_data(i):
    """This function extracts exclusive products from Amazon"""

    # Look for the productID in the web element
    search_string = i.get_attribute("outerHTML")
    ASIN = re.findall(r'<div data-asin="(.*?)"', search_string)
    clean_ASIN = clean_data(ASIN)

    # Get the element's index
    index = re.findall(r'data-index="(.*?)"', search_string)
    clean_index = clean_data(index)

    pos = int(clean_index) + 1

    try:
        # Find exclusive element
        exclusive_xpath = f"//*[@id='search']/div[1]/div[1]/div/span[1]/div[1]/div[{pos}]/div/div/div/div/div[1]"
        exclusive_icon = i.find_element(By.XPATH, exclusive_xpath)
        try:
            # Check for the appearance of 'Amazon exclusive'
            proof = exclusive_icon.find_element(
                By.CSS_SELECTOR, "span[class='a-badge-text']"
            ).get_attribute("innerHTML")
            if proof == "Amazon Exclusive":

                return clean_ASIN

        except NoSuchElementException:
            pass

    except NoSuchElementException:
        pass


############################################################################################
def review_data(i, results_dict, clean_barcode, final_link, name, exclusivity):
    """This function looks for the review score and count of products"""

    try:
        # Based off of the relevant items, can we search for review data
        review_data = i.find_element(
            By.CSS_SELECTOR,
            "div[class='a-section a-spacing-none a-spacing-top-micro']",
        )

        # Find the review average (e.g. 4.5 out of 5 stars)
        review_average = review_data.find_element(
            By.CSS_SELECTOR, "span[class='a-icon-alt']"
        ).get_attribute("innerHTML")
        clean_review_average = review_average.replace(" out of 5 stars", "")

        # Find the review count (e.g. 1000 reviews for this item)
        review_count = review_data.find_element(
            By.CSS_SELECTOR, "span[class='a-size-base s-underline-text']"
        ).get_attribute("innerHTML")
        clean_review_count = clean_data(review_count)

        # Update our dictionary with the relevant information
        results_dict.update(
            {
                clean_barcode: {
                    "barcode type": "ASIN",
                    "link": final_link,
                    "name": name,
                    "review score": float(clean_review_average),
                    "review count": int(clean_review_count),
                    "exclusive": exclusivity,
                }
            }
        )

    except NoSuchElementException:
        # No data so populate the dictionary with empty results
        results_dict.update(
            {
                clean_barcode: {
                    "barcode type": "ASIN",
                    "link": final_link,
                    "name": name,
                    "review score": "N/A",
                    "review count": 0,
                    "exclusive": exclusivity,
                }
            }
        )

    return results_dict


############################################################################################
def product_info_scrape(browser, scraped_dict):
    """This function opens each product link and extracts the brand/manufacturer
    and product or item number if available """

    # Loop through keys in dictionary
    for iKey in scraped_dict.keys():
        product_link = scraped_dict[iKey]["link"]

        # Open up product page
        browser.get(product_link)

        try:
            # Look for product item model number
            technical_details = browser.find_element(
                By.CSS_SELECTOR, "table[class='a-keyvalue prodDetTable']"
            )
            technical_details_row = technical_details.find_elements(By.TAG_NAME, "tr")

            substring1 = "Item model number"
            substring2 = "Manufacturer reference"
            substring3 = "Model Number"

            # Set 'MPN' to 'No Result' by default
            scraped_dict[iKey].update({"MPN": "No Result"})

            # Loop through rows in table
            for i in technical_details_row:
                result = i.text
                # print(result)
                delimiter = substring1 + "|" + substring2 + "|" + substring3
                # If there is a mention of the substrings, gather relevant data
                if substring1 in result or substring2 in result or substring3 in result:
                    model_name = re.split(delimiter, result)

                    scraped_dict[iKey].update({"MPN": model_name[1].strip()})

        except NoSuchElementException:
            # print('exception')
            scraped_dict[iKey].update({"MPN": "No Result"})

        try:
            # Look for brand information
            product_info = browser.find_element(
                By.CSS_SELECTOR, "table[class='a-normal a-spacing-micro']"
            )
            brand_result = product_info.find_element(
                By.CSS_SELECTOR, "tr[class='a-spacing-small po-brand']"
            )
            brand = brand_result.find_element(
                By.CSS_SELECTOR, "span[class='a-size-base po-break-word']"
            ).get_attribute("innerHTML")

            # Populate dictionary with result
            scraped_dict[iKey].update({"brand": brand})

        except NoSuchElementException:

            # If no brand information exists, populate dictionary with no result
            scraped_dict[iKey].update({"brand": "No Result"})

    return scraped_dict


############################################################################################
def amazon_main_func(search_query, amazon_link):
    """This function runs all webscraping cleaning functions"""

    # Instantiate browser
    browser = emulate_browser("webdriver")

    # Scrape product listings
    scraped_dict = amazon_scrape(browser, search_query, amazon_link)

    # Scrape brand information
    updated_dict = product_info_scrape(browser, scraped_dict)

    # Close browser window
    browser.close()

    # Filter out any irrelevant results
    clean_amazon_dict = clean_dict(updated_dict)

    # Remove descriptions and keep name
    final_amazon_dict = clean_name(clean_amazon_dict)

    return final_amazon_dict
