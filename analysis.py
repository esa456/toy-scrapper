"""This is the script where our analysis will take place"""
############################################################################################
import pandas as pd
import re
from amazon import amazon_main_func
from argos import argos_main_func
from smythstoys import smyths_main_func


############################################################################################
def scrape_all_data_into_single_repo():
    """This function runs our retailer scripts and returns a dictionary of data for each"""

    search_query = "jurassic world toys"

    # Retrieve formatted Amazon results and return dictionary
    amazon_link = "https://www.amazon.co.uk"
    amazon_dict = amazon_main_func(search_query, amazon_link)

    # Retrieve formatted Argos results and return dictionary
    argos_link = "https://www.argos.co.uk"
    argos_dict = argos_main_func(search_query, argos_link)

    # Retrieve formatted Smyths Toys results and return dictionary
    smyths_link = "https://www.smythstoys.com"
    smyths_dict = smyths_main_func(search_query, smyths_link)

    # Combine three dictionaries into a dataframe
    repository = merge_dicts_to_dataframe(amazon_dict, argos_dict, smyths_dict)

    # Runs the analysis functions
    results = analysis(repository)

    return results


############################################################################################
def merge_dicts_to_dataframe(dict1, dict2, dict3):
    """This functions converts the dictionaries into a dataframe"""

    # Convert dictionaries to data frames
    df1 = pd.DataFrame.from_dict(dict1, orient="index")
    df2 = pd.DataFrame.from_dict(dict2, orient="index")
    df3 = pd.DataFrame.from_dict(dict3, orient="index")

    # Concatenate the data frames vertically
    merged_df = pd.concat([df1, df2, df3], axis=0)

    # Reset the index and set the keys as the index
    merged_df.reset_index(inplace=True)
    merged_df.set_index("index", inplace=True)

    return merged_df


############################################################################################
def analysis(repository):
    """This is where analysis for the dataframe is performed"""

    # Brand/Manufacturers list
    brands = brand(repository)

    # Groups of linked/associated brands
    brand_groups = {
        "mattel": [
            "fisher price",
            "fisher-price",
            "imaginext",
            "mattel",
            "mattel games",
            "fisher price imaginext",
            "matchbox jurassic world",
            "hot wheels",
        ],
        "whitehouse leisure": ["whitehouse leisure", "posh paws", "whl"],
        "jurassic world": ["jurassic world", "jurassic world toys"],
    }

    # Update brands cols with brand
    updated_df = update_brand(repository, brands)

    # Normalise brands to reflect grouping
    common_brand(updated_df, brand_groups)

    # update MPN
    lego_df = update_MPN_with_brand_and_5digit(updated_df)

    # Find common products across all 3 sites
    common_df = common_products(lego_df)

    # Review Data
    amazon_average_review_count = review(updated_df, "ASIN")
    argos_average_review_count = review(updated_df, "EAN")
    smyths_average_review_count = review(updated_df, "REF")

    return [
        updated_df,
        lego_df,
        common_df,
        amazon_average_review_count,
        argos_average_review_count,
        smyths_average_review_count,
    ]


############################################################################################
def brand(repository):
    """This function gives us a list of brands"""

    brandList = []
    # Loop through values in the brand col
    for element in repository["brand"]:
        # Add all populated rows values to list
        if element != "No Result":
            # Make all elements lowercase
            brandList.append(element.lower())

    # Remove duplicates
    brands = set(brandList)

    return brands


############################################################################################
def update_brand(repository, brands):
    """This function looks for the mention of a brand in the names"""

    for brand in brands:
        if brand != "urassic world":
            repository.loc[
                repository["name"].str.lower().str.contains(brand.lower()), "brand"
            ] = brand

    return repository


############################################################################################
def update_MPN_with_brand_and_5digit(df):
    """This function updates MPN"""

    # Loop through dataframe
    for index, row in df.iterrows():
        brand = row["brand"]
        name = row["name"]

        if isinstance(brand, str):
            # Check if brand name is in the product name, regardless of case sensitivity
            if re.search(brand, name, re.I):
                # Look for a five digit number
                five_digit_number = re.search(r"\b\d{5}\b", name)

                if five_digit_number:
                    # If a five digit number is found, update the MPN field with that number
                    df.at[index, "MPN"] = five_digit_number.group()
        else:
            print(f"Skipping row {index}, 'brand' is not a string: {brand}")

    return df


############################################################################################
def common_brand(df, brand_groups):
    """This function Assign the brand group based on brand name
    leave non-associated brands as is"""

    df["brand"] = df["brand"].apply(
        lambda x: next(
            (
                brand_group
                for brand_group, brands in brand_groups.items()
                if x in brands
            ),
            x,
        )
    )

    return df


############################################################################################
def review(df, string):
    """This function ascertains the review average across all products for a retailer"""

    filtered_df = df[df["barcode type"] == string]
    sum_of_reviews = filtered_df["review count"].sum()
    count = len(filtered_df)

    average = sum_of_reviews / count

    return average


############################################################################################
def common_products(repository):
    """This function retrieves products found across all 3 sites"""

    # Group dataframe by product name and brand
    grouped_df = repository.groupby(["MPN", "brand"]).size().reset_index(name="count")

    # Filter dataframe to only include products in 3 sites
    common_products = grouped_df[
        (grouped_df["count"] == 3) & (grouped_df["MPN"] != "No Result")
    ]

    common_product_names = common_products["brand"]
    common_product_brands = common_products["MPN"]
    # Retrieve the links for common items
    common_product_links = repository[
        (repository["brand"].isin(common_product_names))
        & (repository["MPN"].isin(common_product_brands))
    ]["link"]

    return common_product_links


############################################################################################
def main():
    """This is the main function"""


if __name__ == "__main__":
    results = scrape_all_data_into_single_repo()

    for result in results:
        print(result)
