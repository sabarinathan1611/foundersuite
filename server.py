import time
import logging
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os
# from SMS import sms
# from Call import call
import tempfile

# MongoDB connection setup
client = MongoClient("mongodb+srv://pydevil:B0Qos3zYDIYfoVyp@capitalreachai.1d0li.mongodb.net/?retryWrites=true&w=majority&appName=CapitalReachAI")  # Change this URI to match your MongoDB setup
# client = MongoClient("mongodb://localhost:27017/") 
db = client['foundersuite_data']
collection = db['investor_data']
backup=db["backup"]
log_collection=db["log"]

def findLastPage():
    """
    Retrieves and prints the last page number from the MongoDB collection.
    """
    try:
        # Find the document with the highest page number
        last_page_doc = collection.find_one(sort=[("Page", -1)])  # Replace "Page" with the actual field name
        if last_page_doc:
            last_page = last_page_doc.get("Page", "No page field found")
            print(f"Last page found: {last_page}")
            return last_page
        else:
            print("No documents found in the collection.")
            return None
    except Exception as e:
        print(f"Error while finding the last page: {e}")
        return None

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def log_to_db(level, message):
    """
    Logs a message to the MongoDB log collection.
    """
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "level": level,
        "message": message
    }
    log_collection.insert_one(log_entry)


def setup_driver_with_buster():
    chrome_options = Options()
    
    # Add headless mode and required options for headless environments
    chrome_options.add_argument("--headless=new")  # Use improved headless mode
    chrome_options.add_argument("--no-sandbox")  # Disable sandboxing for compatibility in containerized environments
    chrome_options.add_argument("--disable-dev-shm-usage")  # Prevent /dev/shm from being overused
    chrome_options.add_argument("--disable-gpu")  # Disable GPU rendering
    chrome_options.add_argument("--remote-debugging-port=9222")  # Enable remote debugging
    
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Path to the .crx file for the Buster extension
    extension_path = os.path.abspath("HLIFKPHOLLLIJBLKNNMBFAGNKJNEAGID_0_2_1_0.crx")
    chrome_options.add_extension(extension_path)

    # Specify Chrome binary location
    chrome_options.binary_location = "/opt/google/chrome/chrome"

    # Setup WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    time.sleep(5)
    # Verify that the extension is loaded by opening its popup
    try:
        logger.info("Opening Buster extension...")
        log_to_db("INFO","Opening Buster extension...")
        driver.get("chrome-extension://hlifkpholllijblknnmbfagnkjneagid/popup/popup.html#/")
        time.sleep(3)
        logger.info("Buster extension opened successfully.")
        log_to_db("INFO","Buster extension opened successfully")
    except Exception as e:
        logger.warning(f"Failed to open Buster extension: {e}")
        log_to_db("WARNING",f"Failed to open Buster extension: {e}")
    return driver


driver = setup_driver_with_buster()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Login function
def login():
    logger.info("Navigating to login page...")
    driver.get("https://foundersuite.com/app/log_in")
    time.sleep(2)
    # logdb.insert_one({"Message":"Login"})    
    email_elem = driver.find_element(By.NAME, "email")
    password_elem = driver.find_element(By.NAME, "password")
    email_elem.send_keys("venkatboyalla@nyu.edu")
    password_elem.send_keys("FounderSuite@123")
    password_elem.send_keys(Keys.RETURN)
    logger.info("Logging in...")
    time.sleep(5)
    


def ensure_logged_in():
    """
    Ensures the user is logged in by monitoring for the login page and performing login if necessary.
    """
    logger.info("Checking if login page is displayed...")
    while True:
        try:
            # Wait for the login page to appear
            WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            logger.info("Login page detected. Performing login...")
            log_to_db("INFO","Login page detected. Performing login...")
            # Perform login
            email_elem = driver.find_element(By.NAME, "email")
            password_elem = driver.find_element(By.NAME, "password")
            email_elem.clear()
            email_elem.send_keys("venkatboyalla@nyu.edu")
            password_elem.clear()
            password_elem.send_keys("FounderSuite@123")
            password_elem.send_keys(Keys.RETURN)
            
            logger.info("Login attempt complete. Waiting for the page to load after login...")
            
            # Wait for the post-login page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'css-spwthg'))
            )
            logger.info("Login successful and main page loaded.")
            log_to_db("INFO","Login successful and main page loaded.")
            break  # Exit the loop once logged in and page is loaded
        except TimeoutException:
            logger.info("Login page not detected. Assuming user is already logged in.")
            break  # Exit the loop if login page is not detected
        except Exception as e:
            logger.error(f"Error during login process: {e}")
            log_to_db("ERROR",f"Error during login process: {e}")
            break


def monitor_captcha():
    try:
        logger.info("Checking for captcha...")
        
        # Wait for a specific duration to check for the captcha
        wait = WebDriverWait(driver, 15)  # Wait up to 10 seconds

        while True:
            try:
                
                # Check if captcha element is present
                captcha_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'css-qsjm6s')))
                if captcha_element.is_displayed():
                    logger.warning("Captcha detected! ")
                    log_to_db("INFO","Captcha detected! ")
                    try:
                       
                        
                        
                        time.sleep(40)
                        

                        # Click the Confirm button after solving
                        logger.info("Locating and clicking the Confirm button...")
                        confirm_button = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.css-zlgwmj"))
                        )
                        confirm_button.click()
                        logger.info("Confirm button clicked. Captcha process completed.")
                        log_to_db("INFO","Confirm button clicked. Captcha process completed.")
                        
                        time.sleep(2)
                    except Exception as e :
                        logger.warning(e)
                        log_to_db("WARNING",f" Captcha ERROR: {e}")
                    # input("Press Enter after solving the captcha to continue...")
                else:
                    break  # Exit loop if captcha is no longer displayed
            except TimeoutException:
                logger.info("No captcha detected. Proceeding...")
                return True  # No captcha found, proceed with the script

    except Exception as e:
        logger.error(f"Error while monitoring captcha: {e}")
        log_to_db("ERROR",f"Error while monitoring captcha: {e}")
        return False





# Wait for the page to load fully
def page_loaded():
    logger.info("Waiting for the page to load...")
    log_to_db("INFO","Waiting for the page to load...")
    while True:
        try:
            # We use a class that's always present once the page is fully loaded
            driver.find_element(By.CLASS_NAME, 'css-spwthg') 
            logger.info("Page fully loaded.")
            log_to_db("INFO","Page fully loaded.")
            
            break
        except Exception as e:
            logger.debug("Page is still loading...")
            time.sleep(2)
            
            ensure_logged_in()
            time.sleep(2)


def scrape_connected_people(driver):
    """
    Scrapes connected people information from the current page.
    """
    connected_people = []
    unique_contacts = set()  # To avoid duplicate contacts

    try:
        # Try clicking the action button
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".action button"))
            )
            btn.click()
            time.sleep(1)
        except Exception:
            logger.info("No action button found.")

        time.sleep(1)
        
        # Check for `data-overlay-container="true"`
        overlay_container = driver.find_elements(By.CSS_SELECTOR, "div[data-overlay-container='true']")
        
        if overlay_container:
            # Collect data from inside `div.css-1g5moa9` within the `css-1ymk1q4` container
            logger.info("Using updated logic: Collecting data from 'css-1ymk1q4' elements inside 'css-1g5moa9'.")
            
            # Locate the parent container `css-1ymk1q4`
            container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "css-1ymk1q4"))
            )
            
            # Narrow down to `div.css-1g5moa9`
            sub_container = container.find_element(By.CLASS_NAME, "css-1g5moa9")
            
            # Find all contact elements within the sub-container
            contact_elements = sub_container.find_elements(By.CSS_SELECTOR, "ul.list > li[data-testid='contact-person']")
        else:
            # Fallback to the default logic
            logger.info("Using fallback logic: Collecting data from 'ul.list > li[data-testid=\"contact-person\"]'.")
            contact_elements = driver.find_elements(By.CSS_SELECTOR, "ul.list > li[data-testid='contact-person']")

        logger.info(f"Found {len(contact_elements)} contact person entries.")

        # Iterate through each contact person entry
        for index, contact in enumerate(contact_elements):
            retry_attempts = 3  # Number of retry attempts for stale element
            while retry_attempts > 0:
                try:
                    # Re-locate the element on each retry to handle stale element reference
                    contact = contact_elements[index]

                    # Extract Name
                    name_elements = contact.find_elements(By.CLASS_NAME, "css-piu05e")
                    name = name_elements[0].text if name_elements else "N/A"
                    
                    # Extract Position
                    position_elements = contact.find_elements(By.CLASS_NAME, "position")
                    position = position_elements[0].text if position_elements else "N/A"
                    
                    # Extract Email
                    email_elements = contact.find_elements(By.CLASS_NAME, "css-ybhwie")
                    email = email_elements[0].text if email_elements else "N/A"
                    
                    # Extract Social Media Links
                    social_media = []
                    social_media_elements = contact.find_elements(By.CSS_SELECTOR, "div.socialMedia a")
                    for sm_element in social_media_elements:
                        social_media.append(sm_element.get_attribute("href"))
                    
                    # Create unique ID (email or name + position)
                    unique_id = (email, name, position)

                    # Skip duplicates
                    if unique_id in unique_contacts:
                        logger.info(f"Skipping duplicate contact: {unique_id}")
                        break
                    unique_contacts.add(unique_id)
                    
                    # Append the contact data to the result list
                    connected_people.append({
                        "Name": name,
                        "Position": position,
                        "Email": email,
                        "SocialMedia": social_media
                    })
                    break  # Exit the retry loop
                except Exception as e:
                    retry_attempts -= 1
                    logger.warning(f"Error extracting data for a contact person (retrying {3 - retry_attempts}/3): {e}")
                    log_to_db("WARNING",f"Error extracting data for a contact person (retrying {3 - retry_attempts}/3): {e}")
                    if retry_attempts == 0:
                        logger.error(f"Failed to process contact due to persistent error: {e}")
                        log_to_db("ERROR",f"Failed to process contact due to persistent error: {e}")
                        

    except Exception as e:
        logger.warning(f"Error locating contact person elements: {e}")
        log_to_db("WARINIG",f"Error locating contact person elements: {e}")
        

    logger.info(f"Scraped {len(connected_people)} connected people.")
    return connected_people




def scrape_firm(page_num, driver):
    current_fund_size=0
    sweet_spot=0
    """Scrape data for a firm."""
    try:
        # driver.refresh() 
        time.sleep(1) 
        
        ensure_logged_in()
        
        page_loaded()
        time.sleep(1) 
        # current_fund_size,sweet_spot=""
        
        
        
        
        # Firm header and location
        firmheader = driver.find_element(By.CLASS_NAME, 'css-spwthg').find_element(By.TAG_NAME, 'h1').text

        try:
            # Locate the location element
            location_elements = driver.find_elements(By.CLASS_NAME, 'location')
            location = location_elements[0].find_element(By.TAG_NAME, 'span').text if location_elements else "N/A"
            logger.info(f"Location found: {location}")
        except Exception as e:
            logger.warning(f"Unable to locate location element: {e}")
            log_to_db("WARNING",f"Unable to locate location element: {e}")
            location = "N/A"

        
        logger.info(f"Scraped firm: {firmheader}, Location: {location}")
        
        # typeofinvest=driver.find_element(By.CLASS_NAME, 'css-1wi9cm3').find_element(By.CLASS_NAME, 'css-1wi9cm3').text
        try:
            stage_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-testid='stage-focus-list'] > li.css-tlfg24")
            stage_focus = [stage.text for stage in stage_elements]
            # logger.info(f"Extracted stage focus list: {stage_focus}")
        except Exception as e:
            logger.warning(f"Error extracting stage focus list: {e}")
            log_to_db("WARNING",f"Error extracting stage focus list: {e}")
          
          
        try:
            type_section = driver.find_element(By.CSS_SELECTOR, "section.css-1wi9cm3")
            print("\t\n\n\n\n\ttype_section :",type_section.text,"\t\n\n\n\n\t")
            firm_type_element = type_section.find_element(By.CSS_SELECTOR, "span.css-2ddsc7")
            typeofinvest = firm_type_element.text
            logger.info(f"Extracted firm type: {typeofinvest}")
        except NoSuchElementException:
            logger.info("Firm type section not found.")
        except Exception as e:
            logger.warning(f"Error extracting firm type: {e}")
            log_to_db("WARNING",f"Error extracting firm type: {e}")
          
          
        # Extract Current Fund Size
        try:
            fund_size_sections = driver.find_elements(By.CSS_SELECTOR, "section.css-1wi9cm3")
            for section in fund_size_sections:
                header = section.find_element(By.CSS_SELECTOR, "header.css-1pijdg3").text
                if "Current fund size" in header:
                    current_fund_size = section.find_element(By.CSS_SELECTOR, "span.css-tlfg24").text
                    break
            logger.info(f"Extracted current fund size: {current_fund_size}")
        except Exception as e:
            logger.warning(f"Error extracting current fund size: {e}")
            log_to_db("ERROR",f"Error extracting current fund size: {e}")

        # Extract Sweet Spot
        try:
            sweet_spot_sections = driver.find_elements(By.CSS_SELECTOR, "section.css-18exx4i")
            for section in sweet_spot_sections:
                header = section.find_element(By.CSS_SELECTOR, "header.css-1pijdg3").text
                if "Sweet spot" in header:
                    sweet_spot = section.text.replace(header, "").strip()  # Extract everything except the header
                    break
            logger.info(f"Extracted sweet spot: {sweet_spot}")
            
        except Exception as e:
            logger.warning(f"Error extracting sweet spot: {e}")
            log_to_db("Error",f"Error extracting sweet spot: {e}")





     
            #css-llapv9
            
        Industryfocus= driver.find_elements(By.CSS_SELECTOR, "div.css-llapv9")
        Industryfocutext = [Industryfocu.text for Industryfocu in Industryfocus]
        

        
        # Social Media Links
        social_media_links = []
        social_media_elements = driver.find_elements(By.CSS_SELECTOR, "address.socialMedia a")
        social_media_links = [a.get_attribute("href") for a in social_media_elements]
        
        
        time.sleep(1)
        # Extract connected people info
        connected_people = scrape_connected_people(driver)
        time.sleep(1)
        try:
            # Use XPath to find the button with a specific CSS class and aria-label attribute
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'css-943vzp') and @aria-label='Close']"))
            )
            btn.click()
            time.sleep(1)
        except Exception:
            logger.info("No action button found.")
            # log_to_db("")

        logger.info(f"Scraped {len(connected_people)} connected people for {header}.")

        return {
            'Page': page_num,
            'Type': "firm",
            'InvestmenType':typeofinvest,
            "stage_focus":stage_focus,
            'header': firmheader,
            'location': location,
            "Currentfundsize":current_fund_size,
            "Sweetspot":sweet_spot,
            "Industryfocus":Industryfocutext,
            'socialMedia': social_media_links,
            "status": "new",
            "statusUpdatedAt": datetime.utcnow(),
            'connected_people': connected_people
        }
    except Exception as e:
        logger.warning(f"Error scraping firm: {e}")
        return {}

def scrape_investor(page_num,driver):
    """Scrape data for an investor."""
    page_loaded()
    try:
        location="N/A"
        email="N/A"
        header="N/A"
        email="N/A"
        try : 

            header = driver.find_element(By.CLASS_NAME, 'css-spwthg').find_element(By.TAG_NAME, 'h1').text 
            try:
                # Locate the location element
                location_elements = driver.find_elements(By.CLASS_NAME, 'location')
                location = location_elements[0].find_element(By.TAG_NAME, 'span').text if location_elements else "N/A"
                logger.info(f"Location found: {location}")
            except Exception as e:
                logger.warning(f"Unable to locate location element: {e}")
                location = "N/A"
            email_elements = driver.find_elements(By.CLASS_NAME, 'email') 
            email = email_elements[0].find_element(By.TAG_NAME, 'span').text 
            logger.info(f"Scraped investor: {header}, Location: {location}")
        except Exception as e:
            logger.warning(e)

        
        try:
            type_section = driver.find_element(By.CSS_SELECTOR, "section.css-1wi9cm3")
            print("\t\n\n\n\n\ttype_section :",type_section.text,"\t\n\n\n\n\t")
            firm_type_element = type_section.find_element(By.CSS_SELECTOR, "span.css-2ddsc7")
            typeofinvest = firm_type_element.text
            logger.info(f"Extracted firm type: {typeofinvest}")
        except NoSuchElementException:
            logger.info("Firm type section not found.")
        except Exception as e:
            logger.warning(f"Error extracting firm type: {e}")
            log_to_db("WARINING",f"Error extracting firm type: {e}")
        
        
                # typeofinvest=driver.find_element(By.CLASS_NAME, 'css-1wi9cm3').find_element(By.CLASS_NAME, 'css-1wi9cm3').text
        try:
            stage_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-testid='stage-focus-list'] > li.css-tlfg24")
            stage_focus = [stage.text for stage in stage_elements]
            # logger.info(f"Extracted stage focus list: {stage_focus}")
        except Exception as e:
            logger.warning(f"Error extracting stage focus list: {e}")
            log_to_db("WARNING",f"Error extracting stage focus list: {e}")
                    
        Industryfocus= driver.find_elements(By.CSS_SELECTOR, "div.css-llapv9")
        Industryfocutext = [Industryfocu.text for Industryfocu in Industryfocus]
        
        

            
            
            
        # Extract social media links
        social_media_links = []
        social_media_elements = driver.find_elements(By.CSS_SELECTOR, "address.socialMedia a")
        social_media_links = [a.get_attribute("href") for a in social_media_elements]
                    
        try:
            btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".css-943vzp button"))
                )
            btn.click()
            time.sleep(1)
        except Exception:
            logger.info("No action button found.")
        print("Location :",location)

        return {
            'Page': page_num,
            'Type': "investor",
            'header': header,
            'location': location,
            "InvestmenType":typeofinvest,
            "stage_focus":stage_focus,
            "Industryfocus":Industryfocutext,
            'email': email,
            'socialMedia': social_media_links,            
            "status": "new",
            "statusUpdatedAt": datetime.utcnow(),
        }
    except Exception as e:
        logger.warning(f"Error scraping investor: {e}")
        log_to_db("WARNING",f"Error scraping investor: {e}")
        return {}

def scrape_investor_data(url, page_num):
    """Main function to scrape data from the investor database."""
    logger.info("Navigating to investor database page...")
    driver.get(url)
    time.sleep(1) 
    
    ensure_logged_in()
    monitor_captcha()

    time.sleep(2)
    visited_links = set()
    scraped_data = []

    while True:
        try:
            # Collect links on the current page
            all_links = set()
            investor_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/app/investor_database/investors')]")
            firm_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/app/investor_database/firms/')]")
            time.sleep(4)
            all_links.update([a.get_attribute("href") for a in firm_links+investor_links ])
            logger.info(f"Found {len(all_links)} unique links on the page.")
        except Exception as e:
            logger.warning(f"Error collecting links: {e}")
            log_to_db("WARNING",f"Error collecting links: {e}")
            break

        # Process each link
        for link in all_links:
            if link in visited_links:
                logger.info(f"Link already visited: {link} - Skipping.")
                continue

            logger.info(f"Opening link: {link}")
            visited_links.add(link)

            # Scrape data based on link type
            driver.get(link)
            if "/investor_database/firms/" in link:
                
                page_loaded()
                
                firm=scrape_firm(page_num,driver)
                collection.insert_one(firm)
                print("\n-----------Firm Data Uploaded------------\n")
                scraped_data.append(firm) 
                
            else:
                time.sleep(1) 
                
                ensure_logged_in()
                page_loaded()
                
                
                invest=scrape_investor(page_num,driver)
                collection.insert_one(invest)
                print("\n-----------investor Data Uploaded------------\n")
                
                scraped_data.append(invest)  

        # Save scraped data
        if scraped_data:
            # backup.insert_many(scraped_data)
            logger.info(f"Data from page {page_num} saved to MongoDB.")

        # Move to the next page
        try:
            next_page = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "(//a[@class='css-12dzv40'])[last()]"))
            )
            next_page.click()
            page_num += 1
            logger.info(f"Navigating to page {page_num}...")
            time.sleep(2)
        except Exception as e:
            logger.info("No more pages to scrape.")
            break

    # Save backup
    backup.insert_one({"Page": page_num, "Data": scraped_data})
    logger.info("Backup saved to MongoDB.")
    log_to_db("INFO",f"PAGE {page_num} Completed  ")
    return scraped_data



   
if __name__ == '__main__':
    lastpage=findLastPage()
    
    login()
    for i in range(int(lastpage)+1,11362):
        time.sleep(5)
        
        url=f'https://foundersuite.com/app/investor_database?page={i}'
        print("Page complted ",scrape_investor_data(url,i))
        time.sleep(5)
        
        
    
