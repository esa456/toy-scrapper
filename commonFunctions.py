"""This file holds functions used commonly through out the system"""
############################################################################################
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

############################################################################################
def clean_data(link):
    """This function cleans strings"""

    link = str(link)
    link = link.replace("[", "")
    link = link.replace("]", "")
    link = link.replace('"', "")
    link = link.replace(" ", "")
    link = link.replace(",", "")
    link = link.replace(")", "")
    link = link.replace("(", "")
    link = link.replace("&lrm;", "")
    data = link.replace("'", "")

    return data


############################################################################################
def emulate_browser(string):
    """This function instantiates the browser"""

    if string == "webdriver":
        options = Options()
        # options.add_argument("--headless")
        browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

    if string == "uc":
        # options = Options()
        # options.add_argument("--headless")
        browser = uc.Chrome(driver_executable_path=ChromeDriverManager().install())

    return browser


############################################################################################
def clean_dict(finished_argos_dict):
    """This function deletes all entries that don't have associated IP with the franchise"""

    # Create new list
    delete_list = []

    # Loop through completed dictionary
    for iKey in finished_argos_dict.keys():
        name = finished_argos_dict[iKey]["name"]

        # Look for associated IP
        if "Jurassic World" in name or "Jurassic Park" in name:
            print(name)

        else:
            # If it doesn't contain IP, add to list
            delete_list.append(iKey)

    # Delete items from dictionary
    for j in delete_list:
        del finished_argos_dict[j]

    return finished_argos_dict


############################################################################################
def clean_name(results_dict):
    """This function removes the description from the name"""

    # Loop through dictionary
    for iKey in results_dict.keys():
        name = results_dict[iKey]["name"]

        # If name contains ',' or '|'
        if "," in name or "|" in name:
            split_list = re.split(r",|\|", name)

            # Update dictionary
            results_dict[iKey].update({"name": split_list[0]})

    return results_dict


############################################################################################
def get_cookies_xpath(browser, flag, xpath):
    """This function retrieves the cookie button """
    try:
        # Wait for element to appear
        element = WebDriverWait(browser, 30).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )
        # If element is found and flag is false
        if flag == False:
            return element
        # Otherwise click element (flag is True)
        else:
            element.click()
    except:
        print("Element has not appeared")
        return False
