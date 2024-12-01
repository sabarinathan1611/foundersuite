import requests
import gzip
import json
import zlib
import brotli
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from Mongodb import *
def extract_data_from_response(response_body):
    """
    Extract data from the API response.
    """
    if not response_body.strip():
        print("Response body is empty.")
        return None
    try:
        # Parse JSON response
        data = json.loads(response_body)
        total_pages = data["data"]["response_object"]["total_pages"]
        current_page = data["data"]["response_object"]["current_page"]
        investors = data["data"]["response_object"]["investors"]
        slugs = [investor["slug"] for investor in investors]

        # Create the output model
        result = {
            "total_pages": total_pages,
            "current_page": current_page,
            "slugs": slugs
        }
        return result
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except KeyError as e:
        print(f"Missing key in JSON response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error parsing response: {e}")
        return None


def decompress_response_body(body, encoding):
    """
    Decompress the response body based on its encoding.
    """
    try:
        if encoding == 'gzip':
            return gzip.decompress(body).decode('utf-8')
        elif encoding == 'deflate':
            return zlib.decompress(body).decode('utf-8')
        elif encoding == 'br':  # Brotli support
            return brotli.decompress(body).decode('utf-8')
        else:
            # No compression; return the body as is
            return body.decode('utf-8')
    except Exception as e:
        print(f"Error decompressing response body: {e}")
        return None


def generate_request_for_slug(intercepted_request, slug, api_type="firm"):
    """
    Generate the request model for fetching firm or investor data for a specific slug.

    Args:
        intercepted_request: The original intercepted Selenium Wire request object.
        slug (str): The slug for which the request model is to be generated.
        api_type (str): Type of API to use ('firm' or 'investor').

    Returns:
        dict: A dictionary representing the request model for the slug.
    """
    try:
        # Base URL for the API
        base_url = f"https://api.foundersuite.com/v3/accounts/91370/rounds/102708/investor_page/{slug}/{api_type}"
        slug_url = base_url

        # Extract headers from the intercepted request
        headers = dict(intercepted_request.headers)

        # Build the request model
        request_model = {
            "url": slug_url,
            "method": intercepted_request.method,
            "headers": headers,
        }

        print(f"Generated Request Model for {api_type.capitalize()} API - Slug: {slug}")
        print(json.dumps(request_model, indent=4))
        return request_model
    except Exception as e:
        print(f"Error generating request model for slug {slug}: {e}")
        return None


def fetch_page_data_with_exponential_backoff(request_model, retries=5, base_delay=2):
    """
    Fetch data for the given page using the request model with exponential backoff for 429 errors.

    Args:
        request_model (dict): The request model containing the URL and headers.
        retries (int): Maximum number of retries.
        base_delay (int): Base delay in seconds for exponential backoff.

    Returns:
        dict: The JSON response data if the request is successful, or None if it fails.
    """
    delay = base_delay
    for attempt in range(retries):
        try:
            
            response = requests.get(request_model["url"], headers=request_model["headers"])

            
            if response.status_code == 200:
                print("Successfully fetched page data.")
                return response.json()  
            elif response.status_code == 429:
                print(f"Rate limit hit (attempt {attempt + 1}). Retrying after {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # 
            elif response.status_code == 404:
                print("API returned 404 for this request.")
                return None
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching page data: {e}")
            return None
    print("Exceeded maximum retries. Giving up.")
    return None


def fetch_firm_data_with_fallback(intercepted_request, slugs):
    """
    Fetch data for each slug using the firm API. If the firm API returns 404, attempt the investor API.

    Args:
        intercepted_request: The original intercepted Selenium Wire request object.
        slugs (list): List of slug strings to fetch data for.

    Returns:
        dict: A dictionary containing firm or investor data for each slug.
    """
    all_firm_data = {}

    for slug in slugs:
        # Generate the request model for the firm API
        request_model = generate_request_for_slug(intercepted_request, slug, api_type="firm")

        if request_model:
            # Fetch firm data for the current slug
            print(f"Fetching data for slug: {slug}")
            firm_data = fetch_page_data_with_exponential_backoff(request_model)

            if firm_data:
                print(f"Data for {slug} (firm): {json.dumps(firm_data, indent=4)}")
                all_firm_data[slug] = firm_data
                
            else:
                print(f"Firm API returned 404 for slug: {slug}, trying fallback...")
                # Generate request model for the investor API as a fallback
                fallback_request_model = generate_request_for_slug(intercepted_request, slug, api_type="investor")
                fallback_data = fetch_page_data_with_exponential_backoff(fallback_request_model)

                if fallback_data:
                    print(f"Data for {slug} (investor): {json.dumps(fallback_data, indent=4)}")
                    all_firm_data[slug] = fallback_data
                else:
                    print(f"Failed to fetch data for slug: {slug} using fallback API.")
        else:
            print(f"Failed to generate request model for slug: {slug}")

    return all_firm_data


def setup_driver():
    """
    Set up Chrome driver with Selenium Wire.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def insert_firm_data(slug, data):
    """Insert firm data into the MongoDB `firms` collection."""
    db = get_database()
    firms_collection = db["firms"]
    try:
        firms_collection.insert_one({"slug": slug, "firm_data": data})
        print(f"Inserted firm data for slug: {slug}")
    except Exception as e:
        print(f"Error inserting firm data for slug '{slug}': {e}")
        

def update_slug_status(current_page):
    """Update the `firm_data_collected` field for a specific page."""
    db = get_database()
    slug_collection = db["slug"]
    try:
        slug_collection.update_one({"current_page": current_page}, {"$set": {"firm_data_collected": True}})
        print(f"Updated status for current_page: {current_page}.")
    except Exception as e:
        print(f"Error updating slug status in MongoDB: {e}")
        
def get_unprocessed_slugs():
    """Retrieve unprocessed slugs from MongoDB."""
    db = get_database()
    slug_collection = db["slug"]
    record = slug_collection.find_one({"firm_data_collected": False})
    if record:
        return record["current_page"], record["slugs"]
    return None, None

def main():
    url = "https://foundersuite.com/app/investor_database"
    target_api_url = "https://api.foundersuite.com/v3/accounts/91370/rounds/102708/investor_database?page=1"

    email = "fefided876@cpaurl.com"
    password = "fefided876@cpaurl.com"

    driver = setup_driver()
    driver.get(url)

    try:
        print("Attempting to log in...")
        email_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
        email_input.send_keys(email)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        WebDriverWait(driver, 20).until(EC.url_contains("investor_database"))
    except Exception as e:
        print(f"Error during login: {e}")
        driver.quit()
        return

    try:
        print("Waiting for the target API request...")
        WebDriverWait(driver, 30).until(
            lambda d: any(target_api_url in r.url for r in driver.requests)
        )
        print("Target API request intercepted.")
    except Exception as e:
        print(f"Timeout waiting for the target API request: {e}")
        driver.quit()
        return

    for request in driver.requests:
        if target_api_url in request.url and request.response:
            print(f"Captured API request: {request.url}")
            try:
                print("HTTP Status Code:", request.response.status_code)

                # Process response if no CAPTCHA
                raw_body = request.response.body
                content_encoding = request.response.headers.get("content-encoding", "")
                response_body = decompress_response_body(raw_body, content_encoding)
                if response_body is None:
                    print("Failed to decompress response body.")
                    continue

                # Parse the response
                data = extract_data_from_response(response_body)
                if data and data["current_page"] ==1 :
                    print("Extracted Data (Page 1):", data)

                    # Fetch slug data for firm API with fallback
                    slugs = data["slugs"]
                    firm_data = fetch_firm_data_with_fallback(request, slugs)
                    print("firm_data: ",data["current_page"],type(data["current_page"]))
                else : 
                    while True:
                        current_page, slugs = get_unprocessed_slugs()
                        if not slugs:
                            print("All pages processed. Exiting.")
                            break

                        print(f"Processing slugs for page {current_page}...")
                        
                        firm_data = fetch_firm_data_with_fallback(request, slugs)
                        
                        if firm_data:
                            print("current_page :\n :","\n",current_page,"\n")
                            insert_firm_data(slugs, firm_data)
                            update_slug_status(current_page)
                        

            except Exception as e:
                print(f"Error processing response: {e}")
            break
    else:
        print("No matching API request found.")

    driver.quit()


if __name__ == "__main__":
    main()
