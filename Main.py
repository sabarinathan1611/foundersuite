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
from Mongodb import insert_slug

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
            "slugs": slugs,
            "firm_data_collected":False
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


def generate_request_for_next_page(intercepted_request, current_page):
    """
    Generate the request model for simulating the next page call.

    Args:
        intercepted_request: The original intercepted Selenium Wire request object.
        current_page: The current page number.

    Returns:
        A dictionary representing the request model for the next page.
    """
    try:
        # Extract base URL and headers
        base_url = intercepted_request.url.split("?")[0]
        headers = dict(intercepted_request.headers)

        # Extract query parameters and update the page parameter
        query_params = dict(param.split("=") for param in intercepted_request.url.split("?")[1].split("&"))
        query_params["page"] = str(current_page + 1)  # Increment the page number

        # Construct the next page URL
        next_page_url = f"{base_url}?" + "&".join(f"{k}={v}" for k, v in query_params.items())

        # Build the request model
        request_model = {
            "url": next_page_url,
            "method": intercepted_request.method,
            "headers": headers,
        }

        print("Generated Request Model for Next Page:")
        # print(json.dumps(request_model, indent=4))
        return request_model
    except Exception as e:
        print(f"Error generating request model: {e}")
        return None


def fetch_page_data(request_model):
    """
    Fetch data for the given page using the request model.

    Args:
        request_model (dict): The request model containing the URL, headers, and other details.

    Returns:
        dict: The JSON response data if the request is successful, or None if it fails.
    """
    try:
        
        response = requests.get(request_model["url"], headers=request_model["headers"])

    
        if response.status_code == 200:
            print("Successfully fetched page data.")
            return response.json()  
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching page data: {e}")
        return None


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
                delay *= 2  
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching page data: {e}")
            return None
    print("Exceeded maximum retries. Giving up.")
    return None

def handle_captcha(driver):
    """
    Pauses script to allow manual CAPTCHA solving.
    """
    print("CAPTCHA detected. Please solve it manually in the browser.")
    input("Press Enter after solving the CAPTCHA...")
    print("Resuming script...")

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

                # Check if CAPTCHA is required
                if request.response.status_code == 429:
                    response_body = decompress_response_body(request.response.body, request.response.headers.get("content-encoding", ""))
                    if "captcha" in response_body.lower():
                        handle_captcha(driver)
                        continue

                # Process response if no CAPTCHA
                raw_body = request.response.body
                content_encoding = request.response.headers.get("content-encoding", "")
                response_body = decompress_response_body(raw_body, content_encoding)
                if response_body is None:
                    print("Failed to decompress response body.")
                    continue

                print("Decompressed Response Body:")
                # print(response_body)

                # Parse the response
                data = extract_data_from_response(response_body)
                if data:
                    print("Extracted Data (Page 1):", data)
                    insert_slug(data)
                    
                    
                    current_page = data["current_page"]
                    total_pages = data["total_pages"]

                    while current_page < total_pages:
                        next_request_model = generate_request_for_next_page(request, current_page)
                        if next_request_model:
                            next_page_response = fetch_page_data_with_exponential_backoff(next_request_model)
                            if next_page_response:
                                # Extract data using extract_data_from_response
                                next_page_data = extract_data_from_response(json.dumps(next_page_response))
                                if next_page_data:
                                    print(f"Extracted Data (Page {current_page + 1}):", next_page_data)
                                    # add next page slug  DATA logic
                                    print(insert_slug(next_page_data))
                                    
                                    current_page = next_page_data["current_page"]
                                else:
                                    print(f"Failed to extract data for page {current_page + 1}. Exiting.")
                                    break
                            else:
                                print(f"Failed to fetch data for page {current_page + 1}. Exiting.")
                                break
                        else:
                            print("Failed to generate request model for the next page.")
                            break

            except Exception as e:
                print(f"Error processing response: {e}")
            break
    else:
        print("No matching API request found.")

    driver.quit()


if __name__ == "__main__":
    main()


