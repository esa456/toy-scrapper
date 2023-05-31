"""
This file focuses on smyths toys to perform data extraction and manipulation before
all data is pooled together into one single repository
"""

############################################################################################
import re
from time import sleep
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from commonFunctions import (
    emulate_browser,
    clean_data,
    clean_dict,
    clean_name,
    get_cookies_xpath,
)

############################################################################################
def smyths_scrape(browser, search_query, smyths_link):
    """This function scrapes all the search results from our query"""

    # Initial link creation
    end_link = "+".join(search_query.split())
    search_link = "https://www.smythstoys.com/uk/en-gb/search/?text=" + end_link

    browser.get(search_link)

    try:
        # If a cookie popup appears click accept
        get_cookies_xpath(
            browser, True, "//*[@id='cookieLoad']/div/div/div[1]/div[4]/div[1]/button"
        )

    except:
        print("No Cookie popup")

    sleep(3)

    # Return result data into dictionary
    results_dict = search_results(browser, smyths_link)

    # Close browser
    browser.close()

    return results_dict


############################################################################################
def search_results(browser, smyths_link):
    """This function extracts all the product links"""

    results_dict = {}
    i = 0
    # As all results are on one page, we use a while loop
    while True:
        i += 1

        # xpaths for link, name, uniqueID
        link_xpath = f"/html/body/div[8]/div[2]/div[2]/div[3]/div/div[1]/div[2]/div/div[{i}]/div/a"
        name_xpath = f"/html/body/div[8]/div[2]/div[2]/div[3]/div/div[1]/div[2]/div/div[{i}]/div/a/div/div[2]/h5/span"
        ref_xpath = f"/html/body/div[8]/div[2]/div[2]/div[3]/div/div[1]/div[2]/div/div[{i}]/div/a/div/div[1]"

        try:
            # Retrieve link
            link = browser.find_element(By.XPATH, link_xpath).get_attribute("outerHTML")
            product_link = re.findall(r'<a href="(.*?)">', link)
            clean_link = clean_data(product_link)
            full_link = smyths_link + clean_link

            # Retrieve name
            name = browser.find_element(By.XPATH, name_xpath).text

            # Retrieve reference
            reference = browser.find_element(By.XPATH, ref_xpath).text
            ref = re.findall(r"Ref:(\d+)", reference)
            clean_ref = clean_data(ref)

            # Update the results_dict dictionary
            results_dict.update(
                {
                    clean_ref: {
                        "barcode type": "REF",
                        "link": full_link,
                        "name": name,
                        "MPN": "N/A",
                    }
                }
            )

        except:
            # Load more button
            print("Press Load More button!")
            load_more = get_cookies_xpath(
                browser,
                False,
                "/html/body/div[8]/div[2]/div[2]/div[3]/div/div[1]/div[3]/div[1]/div/button",
            )

            try:
                # click load more button
                load_more.click()
            except:
                # Once the button isn't clickable anymore break loop
                print("Can't click Load More button!")
                break
            sleep(1)

    return results_dict


############################################################################################
def product_info_scrape(initial_dict):
    """This function scrapes the exclusive info, brand/manufacturer, review score and count
    if applicable and updates the dictionary"""

    # Loop through keys in dictionary
    for iKey in initial_dict.keys():
        product_link = initial_dict[iKey]["link"]
        browser = emulate_browser("uc")
        browser.get(product_link)

        try:
            # Click cookie popup if avilable
            get_cookies_xpath(
                browser,
                True,
                "//*[@id='cookieLoad']/div/div/div[1]/div[4]/div[1]/button",
            )

        except:
            print("No Cookie popup")

        try:
            # Look for review info if available
            review_info = browser.find_element(
                By.XPATH, "//*[@id='bvReviewsLink']/div[2]"
            ).get_attribute("innerHTML")

        except StaleElementReferenceException:
            # If element is stale, look again
            review_info = browser.find_element(
                By.XPATH, "//*[@id='bvReviewsLink']/div[2]"
            ).get_attribute("innerHTML")

        # Update dictionary with review data
        review_list = get_review_data(review_info)
        if review_list[0] == "" or review_list[1] == "":

            initial_dict[iKey].update({"review score": "N/A", "review count": 0})

        else:
            initial_dict[iKey].update(
                {
                    "review score": float(review_list[0]),
                    "review count": int(review_list[1]),
                }
            )

        try:
            # Look for exclusive sticker
            sticker_link = "/medias/only-at-smyths-icon.svg?context=bWFzdGVyfGltYWdlc3wyMzg4OHxpbWFnZS9zdmcreG1sfGltYWdlcy9oYjkvaDNhLzEwMTQ4ODAxNDEzMTUwLnN2Z3wyZjY1MDZhYjRlNDE0NDIwYWE0NjY0MjdmNGRhZTQzYWE0OGQ1N2Q4MmNmNDA2OTRmMzY4NjY3NTE1NGU2NGZm"
            exclusive_info = browser.find_element(
                By.XPATH, "/html/body/div[7]/section/div/div/div[1]/div/div[1]/span"
            )
            sticker_info = exclusive_info.get_attribute("innerHTML")
            sticker_link_info = re.findall(r'<img src="(.*?)">', sticker_info)
            clean_string = clean_data(sticker_link_info)

            if clean_string == sticker_link:
                exclusive = "Yes"

                # Update dictionary
                initial_dict[iKey].update({"exclusive": exclusive})

        except NoSuchElementException:
            exclusive = "No"

            # Update dictionary if sticker isn't available or exclusive
            initial_dict[iKey].update({"exclusive": exclusive})

        try:
            # Scroll to bottom of page and look for further details
            sleep(1)
            browser.execute_script("window.scrollTo(0, 2000)")
            further_details = browser.find_element(
                By.XPATH, "/html/body/div[7]/div[5]/div/div[2]/div[1]"
            ).text

        except StaleElementReferenceException:
            further_details = browser.find_element(
                By.XPATH, "/html/body/div[7]/div[5]/div/div[2]/div[1]"
            ).text

        # If supplier details are present
        if "Supplier Contact Details" in further_details:
            # Extract supplier info
            details_start = further_details.find("Supplier Contact Details:") + len(
                "Supplier Contact Details:"
            )
            details_end = further_details.find("Supplier Phone:")
            detail = further_details[details_start:details_end].strip()
            extracted_brand = extract_brand(detail)

            # Update dictionary
            initial_dict[iKey].update({"brand": extracted_brand})

        else:
            initial_dict[iKey].update({"brand": "No Result"})

        browser.quit()

    return initial_dict


############################################################################################
def get_review_data(review_info):
    """This function retrieves the review data"""

    # Retrieve review average
    review_average = re.findall(
        r'<span itemprop="ratingValue">(.*?)</span>', review_info
    )
    clean_review_average = clean_data(review_average)

    # Retrieve review count
    review_count = re.findall(r'<span itemprop="reviewCount">(.*?)</span>', review_info)
    clean_review_count = clean_data(review_count)

    return [clean_review_average, clean_review_count]


############################################################################################
def extract_brand(brand):
    """Extract brand from supplier info"""

    # Looks for any string found between an '@' or '.' and '.com'
    pattern = r"[@.]([^@.]+)\.com"
    match = re.search(pattern, brand)

    # Look for match
    if match:
        return match.group(1)
    else:
        return "No Result"


############################################################################################
def smyths_main_func(search_query, smyths_link):
    """This function runs all webscraping and cleaning functions"""

    # Instantiate browser
    browser = emulate_browser("uc")

    # Scrape product listings
    initial_dict = smyths_scrape(browser, search_query, smyths_link)

    # Scrape product info
    finished_smyths_dict = product_info_scrape(initial_dict)

    # Filter out any irrelevant results
    clean_smyths_dict = clean_dict(finished_smyths_dict)

    # Remove descriptions and keep name
    final_smyths_dict = clean_name(clean_smyths_dict)

    return final_smyths_dict
