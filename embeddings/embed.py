import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from google.cloud import storage

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set the path to the ChromeDriver executable
chrome_driver_path = '/usr/bin/chromedriver'  # Update this path as necessary for your environment

# Initialize the WebDriver service
service = Service(executable_path=chrome_driver_path)

# Initialize the WebDriver with the service and options
driver = webdriver.Chrome(service=service, options=chrome_options)

# Set the base URL of the AIX Academy website
base_url = "https://aixacademy.com/"
urls_to_scrape = [base_url]
visited_urls = set()

# Function to get all the links on a page
def get_all_links(url):
    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = soup.find_all('a', href=True)
    page_links = set()
    for link in links:
        href = link['href']
        if href.startswith('/'):
            href = base_url + href.lstrip('/')
        if base_url in href and href not in visited_urls:
            page_links.add(href)
    return page_links

# Crawl the website and collect URLs
while urls_to_scrape:
    current_url = urls_to_scrape.pop(0)
    if current_url not in visited_urls:
        visited_urls.add(current_url)
        new_links = get_all_links(current_url)
        urls_to_scrape.extend(new_links - visited_urls)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 'your-bucket-name'  # Replace with your bucket name
bucket = storage_client.bucket(bucket_name)

# Function to save page content to a Cloud Storage bucket
def save_page_content(url):
    driver.get(url)
    time.sleep(2)  # Wait for the page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)
    file_name = url.replace(base_url, '').replace('/', '_') + '.txt'
    blob = bucket.blob(f'text/{file_name}')
    blob.upload_from_string(text_content)

# Scrape content from each URL and save it
for url in visited_urls:
    save_page_content(url)

# Close the WebDriver
driver.quit()
