import requests
import os
import time
import gzip
import json
from tqdm import tqdm
from datetime import datetime

# --- Configuration ---
# Define the base URL for the NVD CVE data feeds
NVD_BASE_URL = "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-{year}.json.gz"
# The NVD data goes back to 2002
START_YEAR = 2002
# Define the output directory for the raw data
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', '01_raw', 'nvd_cves')
# NVD recommends a delay between requests to their public API
REQUEST_DELAY_SECONDS = 6

def fetch_and_save_nvd_data():
    """
    Fetches NVD CVE data for each year from START_YEAR to the current year,
    decompresses it, and saves it as a JSON file.
    """
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    current_year = datetime.now().year
    
    print(f"Starting NVD data download from {START_YEAR} to {current_year}.")
    print(f"Data will be saved in: {os.path.abspath(OUTPUT_DIR)}")
    print(f"A delay of {REQUEST_DELAY_SECONDS} seconds will be used between requests.")

    # Loop through each year from the start year to the current year
    for year in tqdm(range(START_YEAR, current_year + 1), desc="Fetching NVD Data by Year"):
        
        # Construct the full URL for the given year
        url = NVD_BASE_URL.format(year=year)
        output_filename = f"nvd_cve_{year}.json"
        output_filepath = os.path.join(OUTPUT_DIR, output_filename)

        # Check if the file already exists to avoid re-downloading
        if os.path.exists(output_filepath):
            print(f"\nSkipping {year}, file already exists: {output_filename}")
            continue
        
        try:
            print(f"\nFetching data for {year} from {url}...")
            
            # Make the HTTP GET request
            response = requests.get(url, stream=True)
            
            # Check for a successful response
            response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
            
            # Decompress the gzipped content in memory
            # The content is in bytes, so we use gzip.decompress
            decompressed_content = gzip.decompress(response.content)
            
            # Decode the bytes to a string (UTF-8 is standard for JSON)
            json_data_str = decompressed_content.decode('utf-8')
            
            # Parse the string to a JSON object to validate it
            json_data = json.loads(json_data_str)
            
            # Save the formatted JSON to a file
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
            
            print(f"Successfully saved data for {year} to {output_filename}")
            
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching data for {year}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {year}: {e}")
            
        # Be a good citizen and wait before the next request
        time.sleep(REQUEST_DELAY_SECONDS)
        
    print("\nNVD data download process completed.")


if __name__ == "__main__":
    fetch_and_save_nvd_data()