import sqlite3
import os
import json
from tqdm import tqdm

# --- Configuration ---
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', '01_raw', 'nvd_cves')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', '02_interim', 'cve_database.sqlite')

def create_database_table(cursor):
    """Creates the CVE table if it doesn't already exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cves (
            id TEXT PRIMARY KEY,
            description TEXT,
            published_date TEXT,
            last_modified_date TEXT,
            cvss_v2_score REAL,
            cvss_v2_severity TEXT,
            cvss_v3_score REAL,
            cvss_v3_severity TEXT,
            cwe_id TEXT,
            affected_products TEXT
        )
    ''')
    print("Database table 'cves' is ready.")

def parse_and_insert_data():
    """Parses raw NVD JSON files and inserts relevant data into the SQLite database."""
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    create_database_table(cursor)

    # Get a list of all JSON files in the raw data directory
    json_files = sorted([f for f in os.listdir(RAW_DATA_DIR) if f.endswith('.json')])

    if not json_files:
        print(f"No JSON files found in {RAW_DATA_DIR}. Please run get_nvd_data.py first.")
        return

    print(f"Found {len(json_files)} NVD JSON files to parse.")

    for json_file in tqdm(json_files, desc="Parsing NVD Files"):
        filepath = os.path.join(RAW_DATA_DIR, json_file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cve_items = data.get('CVE_Items', [])
        
        for item in cve_items:
            # --- Extract Core CVE Info ---
            cve_id = item.get('cve', {}).get('CVE_data_meta', {}).get('ID', None)
            if not cve_id:
                continue

            description_data = item.get('cve', {}).get('description', {}).get('description_data', [])
            description = description_data[0].get('value', '') if description_data else ''
            
            published_date = item.get('publishedDate', None)
            last_modified_date = item.get('lastModifiedDate', None)

            # --- Extract CWE (Common Weakness Enumeration) ---
            problem_type_data = item.get('cve', {}).get('problemtype', {}).get('problemtype_data', [{}])
            cwe_id = "N/A"
            if problem_type_data and problem_type_data[0].get('description'):
                cwe_descs = problem_type_data[0].get('description', [])
                if cwe_descs:
                    cwe_id = cwe_descs[0].get('value', 'N/A')

            # --- Extract CVSS Scores (v2 and v3) ---
            impact = item.get('impact', {})
            cvss_v2_score = impact.get('baseMetricV2', {}).get('cvssV2', {}).get('baseScore', None)
            cvss_v2_severity = impact.get('baseMetricV2', {}).get('severity', None)
            
            cvss_v3_score = impact.get('baseMetricV3', {}).get('cvssV3', {}).get('baseScore', None)
            cvss_v3_severity = impact.get('baseMetricV3', {}).get('cvssV3', {}).get('severity', None)

            # --- Extract Affected Products ---
            # This is complex, so we'll simplify by storing a JSON string of product names.
            # A more advanced approach would use a separate table.
            affected_products = []
            vendor_data = item.get('cve', {}).get('affects', {}).get('vendor', {}).get('vendor_data', [])
            for vendor in vendor_data:
                for product in vendor.get('product', {}).get('product_data', []):
                    product_name = product.get('product_name', 'N/A')
                    affected_products.append(product_name)
            
            affected_products_str = json.dumps(affected_products)

            # --- Insert data into the database ---
            # Using 'INSERT OR REPLACE' to handle potential duplicates gracefully
            cursor.execute('''
                INSERT OR REPLACE INTO cves (id, description, published_date, last_modified_date, 
                                            cvss_v2_score, cvss_v2_severity, cvss_v3_score, 
                                            cvss_v3_severity, cwe_id, affected_products)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cve_id, description, published_date, last_modified_date,
                  cvss_v2_score, cvss_v2_severity, cvss_v3_score,
                  cvss_v3_severity, cwe_id, affected_products_str))

        # Commit changes to the database after processing each file
        conn.commit()

    print("\nFinished parsing all files.")
    # Close the database connection
    conn.close()
    print(f"Database saved at: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    parse_and_insert_data()