import os
import time

import firebase_admin
import pandas as pd
from dotenv import load_dotenv
from firebase_admin import credentials, db

from reader import BlueForsLogReader, TritonLogReader  # Import both readers


# --- Helper Function to Determine Fridge Type ---
def get_fridge_type(pc_name: str) -> str:
    if pc_name == "dopey":
        return "Oxford"
    else:
        return "BlueFors"

# --- Upload Functions ---

def upload_data_bluefors(data, log_date):
    """Uploads data from BlueForsLogReader to Firestore, avoiding duplicates."""
    ref = db.reference(f'/{PC_NAME}/{log_date}')

    for log_type, channels in data.items():
        if log_type == 'flow_rate':
            timestamp_str = channels['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            value = channels['value']
            # Use timestamp as part of the key, and .set()
            ref.child('flow_rate').child(timestamp_str.replace(":", "_")).set({
                'timestamp': timestamp_str,
                'value': float(value)
            })
        else:
            for channel, channel_data in channels.items():
                timestamp_str = channel_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = channel_data['value']
                # Use timestamp as part of the key, and .set()
                ref.child(log_type).child(channel).child(timestamp_str.replace(":", "_")).set({
                    'timestamp': timestamp_str,
                    'value': float(value),
                    'channel': channel  # Include channel here
                })

def upload_data_triton(data, log_file_name):
    """Uploads data from TritonLogReader to Firestore, avoiding duplicates, and filtering zeros."""
    log_date = log_file_name.replace(" ", "_").replace(".", "_").split('_')[1]
    log_date = f"{log_date[:2]}-{log_date[2:4]}-{log_date[4:6]}"
    ref = db.reference(f'/{PC_NAME}/{log_date}')
    timestamp_str = data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    data_to_upload = {'timestamp': timestamp_str}

    for key, value in data.items():
        if key != 'timestamp':
            if isinstance(value, (int, float, str, bool)):
                if isinstance(value, (int, float)) and value == 0:
                    continue
                data_to_upload[key] = value
            elif isinstance(value, np.number):
                if float(value) == 0:
                    continue
                data_to_upload[key] = float(value)
            else:
                try:
                    data_to_upload[key] = str(value)
                except:
                    print(f"Could not convert value for {key} to string. Skipping.")

    if len(data_to_upload) > 1:
        # Use timestamp as part of the key, and .set()
        ref.child(timestamp_str.replace(":", "_")).set(data_to_upload)
    else:
        print("No non-zero data to upload (besides timestamp).")

def main(LOGS_FOLDER="logs"):
    """Main loop to continuously monitor logs and upload data."""
    processed_dates = set()
    start_time = time.localtime()  # Record the start time
    latest_log_file = None  # Track the latest log file

    while True:
        # Update present time
        present_time = time.localtime()  # Get current time
        current_date = time.strftime("%Y-%m-%d", present_time)

        # Check if the date has changed
        if latest_log_file is None or current_date != time.strftime("%Y-%m-%d", start_time):
            # Date has changed, find the latest log file
            if get_fridge_type(PC_NAME) == "Oxford":
                log_files = [f for f in os.listdir(LOGS_FOLDER) if f.endswith('.vcl')]
                log_files.sort(reverse=True)  # Most recent first
                if log_files:
                    latest_log_file = log_files[0]  # Update to the latest log file
                    print(f"New log file detected: {latest_log_file}")
                else:
                    print("No .vcl log files found.")
                    time.sleep(60)
                    continue
            else:  # Assume BlueFors
                log_dates = [d for d in os.listdir(LOGS_FOLDER) if os.path.isdir(os.path.join(LOGS_FOLDER, d))]
                log_dates.sort(reverse=True)  # Most recent first
                if log_dates:
                    latest_log_file = log_dates[0]  # Update to the latest log date
                    print(f"New log date detected: {latest_log_file}")
                else:
                    print("No log directories found.")
                    time.sleep(60)
                    continue

            # Update start_time to the current time
            start_time = present_time

        # Process the latest log file
        if get_fridge_type(PC_NAME) == "Oxford":
            log_file_path = os.path.join(LOGS_FOLDER, latest_log_file)
            try:
                log_reader = TritonLogReader(log_file_path)
                latest_data = log_reader.get_latest_entry()
                if latest_data:
                    upload_data_triton(latest_data, latest_log_file)  # Pass the log file name
                else:
                    print("No data found in the latest log file.")

            except Exception as e:
                print(f"Error processing {latest_log_file}: {e}")

        else:  # Assume BlueFors
            try:
                log_reader = BlueForsLogReader(LOGS_FOLDER)
                latest_data = log_reader.get_latest_entry(latest_log_file)
                if latest_data:
                    upload_data_bluefors(latest_data, latest_log_file)
                else:
                    print(f"No data found for {latest_log_file}")

            except Exception as e:
                print(f"Error processing {latest_log_file}: {e}")

        time.sleep(60)  # Check for new logs every 60 seconds

if __name__ == "__main__":
    load_dotenv()

    # --- Firebase Setup ---
    cred = credentials.Certificate(os.getenv('CRED_FILE'))
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv('DB_URL')
    })

    PC_NAME = os.getenv("PC_NAME")
    FRIDGE_TYPE = os.getenv("FRIDGE_TYPE")

    main(os.getenv("LOGFILE_DIR"))