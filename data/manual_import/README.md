# Manual IMD AWS Data Ingestion Folder

This folder allows you to import official IMD AWS observations if you download them via your browser or the IMD API Test Console.

## Step-by-Step Instructions

1. **Log in to the IMD Portal**:  
   Visit [https://api.imd.gov.in/public/index.php](https://api.imd.gov.in/public/index.php) and log in with your credentials (`Deepanshu Kushwaha`).

2. **Open the API Test Console**:  
   Select **API Test Console** from the left navigation menu.

3. **Fetch AWS Data**:  
   - Select **API Endpoint**: `AWS Data` (or `AWS Data Mapping`)
   - Select your active **API Key**
   - Paste your **JWT Bearer Token**
   - Click **Try API**

4. **Save the JSON**:  
   Copy the JSON response output and save it as a file inside this directory:  
   `data/manual_import/aws_data.json`

5. **Run the Ingestion Command**:  
   ```bash
   python tools/import_manual_imd_json.py
   ```

The script will automatically:
- Verify and parse all station records.
- Extract ONLY: Temperature (°C), Pressure (hPa), and Relative Humidity (%).
- Archive the raw payload immutably into `data/raw/imd_aws/` with a cryptographic SHA-256 `.receipt.json`.
- Populate `data/observations/latest_imd_aws.json` for live anomaly detection.
