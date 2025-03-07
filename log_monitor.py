import os
import time

import firebase_admin
import pandas as pd
from dotenv import load_dotenv  # Add this import
from firebase_admin import credentials, db

from reader import \
    BlueForsLogReader  # Assuming your original code is in logger_reader.py

load_dotenv()

# --- Firebase Setup ---
cred = credentials.Certificate(os.getenv('CRED_FILE'))  # Make sure this path is correct
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('DB_URL')  # Read the database URL from the .env file
})

PC_NAME = os.getenv("PC_NAME")
ref = db.reference(f'/{PC_NAME}/')

# --- Log File Handling ---
LOGS_FOLDER = "logs"  # Or the path to your logs folder

def upload_data(data, log_date):
    """Uploads the latest data to Firestore, avoiding duplicates."""
    ref = db.reference(f'/{PC_NAME}/{log_date}') # Moved inside the function

    for log_type, channels in data.items():
        if log_type == 'flow_rate':
            # Handle flow rate separately
            timestamp_str = channels['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            value = channels['value']

            # Check for existing flow_rate entry with the same timestamp
            existing_entry = ref.child('flow_rate').order_by_child('timestamp').equal_to(timestamp_str).get()
            if not existing_entry:
                ref.child('flow_rate').push({
                    'timestamp': timestamp_str,
                    'value': float(value)  # Ensure value is a float
                })
        else: # handle channels
            for channel, channel_data in channels.items():
                timestamp_str = channel_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = channel_data['value']

                # Check for duplicate entry.
                existing_entry = ref.child(log_type).child(channel).order_by_child('timestamp').equal_to(timestamp_str).get()
                if not existing_entry:
                    # Push to a child node with the channel name as the key
                    ref.child(log_type).child(channel).push({
                        'timestamp': timestamp_str,
                        'value': float(value)
                    })

def main():
    """Main loop to continuously monitor logs and upload data."""
    log_reader = BlueForsLogReader(LOGS_FOLDER)
    processed_dates = set()

    while True:
        # Get the most recent log directory
        log_dates = [d for d in os.listdir(LOGS_FOLDER) if os.path.isdir(os.path.join(LOGS_FOLDER, d))]
        log_dates.sort(reverse=True)  # Sort in descending order to get the latest first

        if not log_dates:
            print("No log directories found.")
            time.sleep(60)
            continue

        latest_log_date = log_dates[0]

        if latest_log_date not in processed_dates:
            print(f"Processing new log date: {latest_log_date}")
            try:
                latest_data = log_reader.get_latest_entry(latest_log_date)
                if latest_data:
                    upload_data(latest_data, latest_log_date) # Pass log_date
                    processed_dates.add(latest_log_date) # add to the set
                else:
                    print(f"No data found for {latest_log_date}")

            except Exception as e:
                print(f"Error processing {latest_log_date}: {e}")

        else:
            print(f"Already processed {latest_log_date}, checking for updates...")
            # Even if the date is processed, there might be updates within the same log files.
            try:
                latest_data = log_reader.get_latest_entry(latest_log_date)  # Re-read data.  Crucial for live updates.
                if latest_data:
                    upload_data(latest_data, latest_log_date) # Pass log_date, and check for duplicates within.
                else:
                    print(f"No new data in {latest_log_date}") # No new data found

            except Exception as e:
                print(f"Error processing {latest_log_date} during update check: {e}")

        time.sleep(60)


if __name__ == "__main__":
    main()