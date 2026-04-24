import requests
import pandas as pd
from io import StringIO

# 1. User Credentials
credentials = {
    'identity': 'abuakel30@gmail.com',
    'password': '000'
}

# 2. Your specific Space-Track API URL
api_url = "https://www.space-track.org/basicspacedata/query/class/gp/orderby/TLE_LINE2%20asc/limit/10000/format/csv/emptyresult/show"

# 3. Create a session to maintain login state
with requests.Session() as session:
    try:
        # Perform login via POST request
        login_response = session.post('https://www.space-track.org/ajaxauth/login', data=credentials)
        
        # Check if login was successful
        if login_response.status_code == 200:
            print("Successfully authenticated with Space-Track.")
            
            # Fetch the data using the API URL
            data_response = session.get(api_url)
            
            if data_response.status_code == 200:
                # Convert the CSV text response into a format Pandas can read
                csv_data = StringIO(data_response.text)
                df = pd.read_csv(csv_data)
                
                # Display the first few rows of the extracted data
                print("Data Preview:")
                print(df.head())
                
                # Save the results to a local CSV file for your project
                df.to_csv('orbital_data_export_1.csv', index=False)
                print("\nData saved to 'orbital_data_export.csv'")
            else:
                print(f"Error fetching data: {data_response.status_code}")
        else:
            print(f"Login failed: {login_response.status_code}")
            
    except Exception as e:
        print(f"An unexpected error occurred: {e}")