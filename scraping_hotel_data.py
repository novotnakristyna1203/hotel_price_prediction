import datetime as dt
import time
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# ----------------------------
# 1. Generate dynamic date ranges
# ----------------------------
def generate_simple_dates():
    today = dt.date.today()
    offsets = list(range(0,180))  # days ahead
    date_ranges = []

    for offset in offsets:
        checkin = today + dt.timedelta(days=offset)
        checkout = checkin + dt.timedelta(days=1)
        if checkin.weekday() in [4, 5]:  # Friday or Saturday
            checkout += dt.timedelta(days=1)
        date_ranges.append((
            checkin.strftime("%Y-%m-%d"),
            checkout.strftime("%Y-%m-%d")
        ))
    return date_ranges

# ----------------------------
# 2. Update booking.com URL dates
# ----------------------------
def update_booking_dates(url, new_checkin, new_checkout):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query['checkin'] = [new_checkin]
    query['checkout'] = [new_checkout]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

# ----------------------------
# 3. Setup Selenium for Google Cloud
# ----------------------------
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--enable-unsafe-swiftshader")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Update path to where chromedriver is installed in Cloud Shell
from shutil import which
service = Service(which("chromedriver"))
# ----------------------------
# 4. Load hotel links
# ----------------------------
links_df = pd.read_csv("C:/Users/42072/Desktop/program/scrapy_hotel_links.csv")


if "hotel_link" in links_df.columns:
    column_name = "hotel_link"
elif "hotel_data" in links_df.columns:
    column_name = "hotel_data"
else:
    raise ValueError(f"CSV columns not recognized: {links_df.columns}")

hotel_links = links_df[column_name].dropna().tolist()

# ----------------------------
# 5. Loop through all date ranges
# ----------------------------
date_ranges = generate_simple_dates()

# Create driver once
driver = webdriver.Chrome(service=service, options=chrome_options)

# Make output folder
output_dir = "/home/novotnakristyna1203/hello-world-1/hello-world-2/my_things/scraping_results"
os.makedirs(output_dir, exist_ok=True)

all_rooms_data = []
batch_size = 7  # Save after each 7 days

# Split date_ranges into chunks of 7
for batch_start in range(0, len(date_ranges), batch_size):
    batch = date_ranges[batch_start: batch_start + batch_size]
    batch_start_date = batch[0][0]  # first check-in date in batch
    batch_end_date = batch[-1][0]   # last check-in date in batch
    scraping_date = dt.date.today().strftime("%Y-%m-%d")

    print(f"\n=== Starting batch {batch_start_date} → {batch_end_date} ===")

    for checkin, checkout in batch:
        print(f"\n--- Scraping for {checkin} → {checkout} ---")
        updated_links = [update_booking_dates(link, checkin, checkout) for link in hotel_links]
        
        for link in updated_links:
            print(f"Scraping hotel: {link}")
            driver.get(link)
            time.sleep(5)

            # Try clicking "Show rooms"
            try:
                show_rooms_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.hprt-show-more"))
                )
                show_rooms_button.click()
                time.sleep(2)
            except:
                pass

            # Scrape all room data
            room_blocks = driver.find_elements(By.XPATH, "//tr[contains(@class,'js-rt-block-row')]")
            for block in room_blocks:
                try:
                    room_type = block.find_element(By.XPATH, ".//span[contains(@class,'hprt-roomtype-icon-link')]").text.strip()
                except:
                    room_type = "N/A"

                try:
                    occupancy = block.find_element(By.XPATH, ".//div[contains(@class,'c-occupancy-icons')]//span[contains(@class,'bui-u-sr-only')]").text.strip()
                except:
                    occupancy = "N/A"

                try:
                    highlights_elements = block.find_elements(By.XPATH, ".//div[contains(@class,'bui-spacer--medium')]//span[contains(@class,'bui-badge')]")
                    highlights = [h.text.strip() for h in highlights_elements if h.text.strip()]
                except:
                    highlights = []

                try:
                    price_element = block.find_elements(By.XPATH, ".//div[contains(@class,'hprt-price-block ')]//span[contains(@class,'prco-valign-middle-helper')]")
                    price = [h.text.strip() for h in price_element if h.text.strip()]
                except:
                    price = []

                try:
                    all_element = block.find_elements(By.XPATH, ".//div[contains(@class,'hprt-block ')]")
                    all_info = [h.text.strip() for h in all_element if h.text.strip()]
                except:
                    all_info = []

                all_rooms_data.append({
                    "Room Type": room_type,
                    "Occupancy": occupancy,
                    "Highlights": highlights,
                    "Price": price,
                    "Other Info": all_info,
                    "Hotel Link": link,
                    "Checkin": checkin,
                    "Checkout": checkout,
                    "Scraping Date": scraping_date
                })

    # ✅ Save one Excel file for each 7-day batch
    batch_filename = f"scdate_{scraping_date}_first_in_{batch_start_date}_last_in_{batch_end_date}.xlsx"
    save_path = f"C:/Users/42072/Desktop/program/{batch_filename}"

    df_batch = pd.DataFrame(all_rooms_data)
    df_batch.to_excel(save_path, index=False)
    print(f"💾 Saved {len(all_rooms_data)} rooms to {save_path}")

    # Clear memory after saving this batch
    all_rooms_data = []

# After all batches
driver.quit()
print("\n✅ All date ranges scraped and saved in weekly files!")


