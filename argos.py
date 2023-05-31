"""
This file focuses on argos to perform data extraction and manipulation before
all data is pooled together into one single repository
"""
############################################################################################
import re
from time import sleep
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from commonFunctions import clean_data, emulate_browser, clean_dict, clean_name

############################################################################################
def argos_scrape(browser, search_query, argos_link):
    """This function scrapes all the search results from our query"""

    # Open argos.co.uk
    browser.get(argos_link)

    try:
        # If a cookie pop-up appear click accept
        accept_cookie = browser.find_element(
            By.CSS_SELECTOR, "button[id='consent_prompt_submit']"
        )
        accept_cookie.click()

    except NoSuchElementException:
        print("No Cookie popup")

    # Find the search bar
    search = browser.find_element(By.CSS_SELECTOR, "input[id='searchTerm']")
    search.click()
    sleep(1)

    # Enter the search query into the search bar
    search.send_keys(search_query)
    search.send_keys(Keys.ENTER)
    sleep(2)

    # Return all relevant navigational info
    navigational_info = pagination(browser)

    # Return the number of pages with results
    last_page = navigational_info[-2].get_attribute("innerHTML")

    # Create an empty dictionary
    argos_results_dict = {}
    counter = 1

    # Loop through the pages of results
    for _ in range(1, (int(last_page) + 1)):
        # Each page returns a dictionary of result data
        results_dict = search_results(browser, argos_link)
        sleep(1)

        try:
            # Click the next page button until its no longer clickable
            next_button = navigational_info[-1]

            # Scroll to next button
            browser.execute_script("arguments[0].scrollIntoView(true);", next_button)
            sleep(1)
            next_button.click()
            sleep(2)

        except StaleElementReferenceException:
            # If the element is stale it means we're at the end of results
            print("End of pages")

        # Populate our dictionary with each page of result data as we loop
        argos_results_dict.update({counter: results_dict})
        counter += 1

    return argos_results_dict


############################################################################################
def pagination(browser):
    """This function gathers the page data"""

    pages = browser.find_element(By.CSS_SELECTOR, "nav[role='navigation']")
    page_list = pages.find_elements(By.CSS_SELECTOR, "a[role='link']")

    return page_list


############################################################################################
def search_results(browser, argos_link):
    """This function extracts each page worth of relevant product links"""

    results_dict = {}
    counter = 1

    # Results is a list of all the result elements on the page
    results = browser.find_elements(
        By.CSS_SELECTOR, "a[data-test='component-product-card-title']"
    )

    # Gather all available information on the result
    for i in results:
        result_data = i.get_attribute("innerHTML")

        # Scrape the link to product
        link = re.findall(r'content="(.*?)">', result_data)
        clean_link = clean_data(link)
        final_link = argos_link + clean_link

        # If the link contains this don't scrape
        if "product/tuc" in final_link:
            continue

        # Add to dictionary
        sub_dict = {"link": final_link}

        results_dict.update({counter: sub_dict})
        counter = counter + 1

    return results_dict


############################################################################################
def product_info_scrape(browser, scraped_dict):
    """This function scrapes the name, barcode, review score and count if applicable
    and formats the data in a new dictionary"""

    actual_result_dict = {}
    # loop through dictionary of product links
    for iKey in scraped_dict.keys():
        page = scraped_dict[iKey]

        for j in page:
            product_link = page[j]["link"]

            # Parse link to product page
            browser.get(product_link)
            sleep(1)

            # Retrieve product name
            product_name = browser.find_element(
                By.CSS_SELECTOR, "span[data-test='product-title']"
            ).text

            # Retrieve product barcode
            product_info = browser.find_element(
                By.CSS_SELECTOR, "div[class='product-description-content-text']"
            ).text
            EAN = re.findall(r"EAN:? (\d+)|MPN/UPC/ISBN:? (\d+)", product_info)
            clean_barcode = clean_data(EAN)

            # If the barcode isn't made up of digits, skip it
            if not clean_barcode.isdigit():
                continue

            # Retrieve exclusivity status
            try:
                # exclusive_banner = browser.find_element(By.CSS_SELECTOR, "div[class='BadgeWrapperstyles__Wrapper-vh9kra-0 cerJiS badges-wrapper']")
                info_banner = browser.find_element(
                    By.CSS_SELECTOR,
                    "div[class='Badgesstyles__BadgeWrapper-xfrkcy-1 fHFBWk']",
                ).get_attribute("innerHTML")
                exclusivity = re.findall(r'alt="(.*?)"', info_banner)
                clean_exclusive = clean_data(exclusivity)

                if clean_exclusive == "INFO_exclusive":
                    exclusive = "Yes"

            except NoSuchElementException:
                exclusive = "No"

            try:
                # If the review data is present scrape it
                average_review_data = browser.find_element(
                    By.CSS_SELECTOR,
                    "span[class='Reviewsstyles__TrustmarkMessage-sc-6g3q7a-3 bkuzqy']",
                ).text
                average_review = average_review_data.split("|")[0].strip()

                # Scrape number of reviews for item
                review_count = browser.find_element(
                    By.CSS_SELECTOR, "a[data-test='reviews-flag-link']"
                ).text
                review_count_num = re.findall(r"\d", review_count)
                clean_review_count = clean_data(review_count_num)

                actual_result_dict.update(
                    {
                        clean_barcode: {
                            "brand": "No Result",
                            "barcode type": "EAN",
                            "link": product_link,
                            "name": product_name,
                            "review score": float(average_review),
                            "review count": int(clean_review_count),
                            "MPN": "N/A",
                            "exclusive": exclusive,
                        }
                    }
                )

            except NoSuchElementException:
                # Otherwise populate the review fields with no result
                actual_result_dict.update(
                    {
                        clean_barcode: {
                            "brand": "No Result",
                            "barcode type": "EAN",
                            "link": product_link,
                            "name": product_name,
                            "review score": "N/A",
                            "review count": 0,
                            "MPN": "N/A",
                            "exclusive": exclusive,
                        }
                    }
                )

    return actual_result_dict


############################################################################################
def argos_main_func(search_query, argos_link):
    """This function runs all webscraping and cleaning functions"""

    # Instantiate browser
    browser = emulate_browser("webdriver")

    # Scrape product listings
    scraped_dict = argos_scrape(browser, search_query, argos_link)

    # Scrape product info
    finished_argos_dict = product_info_scrape(browser, scraped_dict)

    # Close browser window
    browser.close()

    # Filter out any irrelevant results
    clean_argos_dict = clean_dict(finished_argos_dict)

    # Remove descriptions and keep name
    final_amazon_dict = clean_name(clean_argos_dict)

    return final_amazon_dict
