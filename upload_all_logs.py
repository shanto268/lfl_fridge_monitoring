import os

import firebase_admin
import pandas as pd
from dotenv import load_dotenv
from firebase_admin import credentials, db

from reader import BlueForsLogReader  # Your log reader

# --- Configuration ---
load_dotenv()
CREDENTIALS_FILE = os.getenv('CRED_FILE')
DATABASE_URL = os.getenv('DB_URL')
PC_NAME = os.getenv('PC_NAME')
LOGS_PARENT_DIRECTORY = "log_archives/bashful"  # The parent directory containing all log date directories

# --- Firebase Setup ---
cred = credentials.Certificate(CREDENTIALS_FILE)
firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

def upload_all_data(parent_dir):
    """Uploads all log entries from all dates in the parent directory to Firebase."""
    log_reader = BlueForsLogReader(parent_dir) # Initialize with the *parent* directory

    for log_date in os.listdir(parent_dir):
        log_date_path = os.path.join(parent_dir, log_date)
        if not os.path.isdir(log_date_path):
            continue  # Skip files, only process directories

        print(f"Processing log date: {log_date}")
        ref = db.reference(f'/{PC_NAME}/{log_date}')  # Database reference for this date

        # --- Temperature, Resistance, Pressure (for each channel) ---
        for log_type in ["temperature", "resistance", "pressure"]:
            df = log_reader.get_logs(log_date, log_type)
            if df.empty:
                print(f"  No {log_type} data for {log_date}")
                continue

            print(f"  Uploading {log_type} data...")
            for channel in range(1, 7):
                channel_data = df[df['channel'] == channel]
                if channel_data.empty:
                    continue

                for index, row in channel_data.iterrows():
                    timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    value = row['value']
                    # Push each entry individually (no duplicate check needed for initial upload)
                    ref.child(log_type).child(f"CH{channel}").push({
                        'timestamp': timestamp_str,
                        'value': float(value)
                    })

        # --- Flowmeter ---
        flowmeter_df = log_reader.get_flowmeter(log_date)
        if not flowmeter_df.empty:
            print(f"  Uploading flowmeter data...")
            for index, row in flowmeter_df.iterrows():
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = row['flow_rate']
                ref.child('flow_rate').push({
                    'timestamp': timestamp_str,
                    'value': float(value)
                })
        #---- Status ---
        status_df = log_reader.get_logs(log_date, "status")
        if not status_df.empty:
            print(f" Uploading status data...")
            for index, row in status_df.iterrows():
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                data_to_upload = {'timestamp': timestamp_str}

                for col in status_df.columns:
                    if col != 'timestamp':
                         data_to_upload[col] = row[col]
                ref.child('status').push(data_to_upload)



def main():
    """Main function to upload all data."""
    print(f"Uploading all log data from '{LOGS_PARENT_DIRECTORY}' to Firebase...")
    upload_all_data(LOGS_PARENT_DIRECTORY)
    print("Data upload complete.")

if __name__ == "__main__":
    main()