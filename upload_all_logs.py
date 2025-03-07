import datetime
import os
import time

import firebase_admin
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from firebase_admin import credentials, db

from reader import BlueForsLogReader, TritonLogReader  # Import both readers

# --- Configuration ---
load_dotenv()
CREDENTIALS_FILE = os.getenv('CRED_FILE')
DATABASE_URL = os.getenv('DB_URL')
PC_NAME = os.getenv('PC_NAME')
LOGS_PARENT_DIRECTORY = os.getenv('LOGFILE_DIR', 'logs')  # Default value
FRIDGE_TYPE = os.getenv("FRIDGE_TYPE", "BlueFors")

# --- Firebase Setup ---
cred = credentials.Certificate(CREDENTIALS_FILE)
firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

# --- Helper Function to Determine Fridge Type ---
def get_fridge_type(pc_name: str) -> str:
    if pc_name == "dopey":
        return "Oxford"
    else:
        return "BlueFors"

# --- Upload Functions ---

def upload_data_bluefors(data, log_date, ref):
    """Uploads BlueFors data to a given Firebase reference."""
    for log_type, channels in data.items():
        if log_type == 'flow_rate':
            timestamp_str = channels['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            value = channels['value']
            ref.child('flow_rate').child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                'timestamp': timestamp_str,
                'value': float(value)
            })
        else:
            for channel, channel_data in channels.items():
                timestamp_str = channel_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                value = channel_data['value']
                ref.child(log_type).child(channel).child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                    'timestamp': timestamp_str,
                    'value': float(value),
                    'channel': channel  # Include channel here
                })

def upload_data_triton(data_df, log_file_name, ref):
    """Uploads Triton data (entire DataFrame) to Firestore, filtering zeros."""

    # Iterate through DataFrame rows
    for index, row in data_df.iterrows():
        try:
            # Correctly handle the 'Time(secs)' column and convert to datetime
            timestamp_secs = row['Time(secs)']
            if not isinstance(timestamp_secs, (int, float, np.number)):
                print(f"Skipping row with invalid timestamp: {timestamp_secs}")
                continue

            timestamp_datetime = datetime.datetime.fromtimestamp(timestamp_secs)
            timestamp_str = timestamp_datetime.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError) as e:
            print(f"Error converting timestamp for row {index}: {e}")
            continue  # Skip to the next row if timestamp conversion fails

        data_to_upload = {'timestamp': timestamp_str}

        for col in data_df.columns:
            if col != 'Time(secs)':  # Correctly check against 'Time(secs)'
                value = row[col]
                if isinstance(value, (int, float, str, bool)):
                    # Filter out zero values (and non-numeric values)
                    if isinstance(value, (int, float)) and value == 0:
                        continue  # Skip zero values
                    data_to_upload[col] = value
                elif isinstance(value, np.number):
                    #Filter out zero values
                    if float(value) == 0:
                        continue
                    data_to_upload[col] = float(value)
                else:
                    try:
                        data_to_upload[col] = str(value)
                    except:
                        print(f"Could not convert value for {col} to string. Skipping.")
        if len(data_to_upload) > 1:  # if more than only timestamp
            ref.child(timestamp_str.replace(":", "_").replace(" ", "_")).set(data_to_upload)
        else:
            print("No non-zero data to upload (besides timestamp).")

def upload_all_data(parent_dir):
    """Uploads all log entries from all dates/files in the parent directory."""
    fridge_type = get_fridge_type(PC_NAME)

    if fridge_type == "Oxford":
        log_reader = TritonLogReader
        for log_file in os.listdir(parent_dir):
            if log_file.endswith(".vcl"):
                log_file_path = os.path.join(parent_dir, log_file)
                print(f"Processing log file: {log_file}")
                log_date = log_file.replace(" ", "_").replace(".", "_").split('_')[1]
                log_date = f"{log_date[:2]}-{log_date[2:4]}-{log_date[4:6]}"
                ref = db.reference(f'/{PC_NAME}/{log_date}')

                try:
                    reader = log_reader(log_file_path)
                    data_df = reader.get_df()  # Get the ENTIRE DataFrame
                    if not data_df.empty: # Check if not empty.
                        upload_data_triton(data_df, log_file, ref) # Pass the dataframe.
                except Exception as e:
                    print(f"Error processing {log_file}: {e}")

    else:  # Assume BlueFors
        log_reader = BlueForsLogReader(parent_dir)
        for log_date in os.listdir(parent_dir):
            log_date_path = os.path.join(parent_dir, log_date)
            if not os.path.isdir(log_date_path):
                continue

            print(f"Processing log date: {log_date}")
            ref = db.reference(f'/{PC_NAME}/{log_date}')

            for log_type in ["temperature", "pressure", "resistance", "flow_rate", "status"]:
                df = log_reader.get_logs(log_date, log_type)
                if df.empty:
                    print(f"  No {log_type} data for {log_date}")
                    continue

                print(f"  Uploading {log_type} data...")
                if log_type in ["temperature", "pressure", "resistance"]:
                    for channel in range(1, 7):
                        channel_data = df[df['channel'] == channel]
                        if channel_data.empty:
                            continue

                        for _, row in channel_data.iterrows():
                            timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                            value = row['value']
                            ref.child(log_type).child(f"CH{channel}").child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                                'timestamp': timestamp_str,
                                'value': float(value),
                                'channel': f"CH{channel}"
                            })
                elif log_type == "flow_rate":
                    for _, row in df.iterrows():
                        timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        value = row['flow_rate']
                        ref.child('flow_rate').child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                            'timestamp': timestamp_str,
                            'value': float(value)
                        })
                elif log_type == "status":
                    for _, row in df.iterrows():
                        timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        data_to_upload = {'timestamp': timestamp_str}
                        for col in df.columns:
                            if col != 'timestamp':
                                data_to_upload[col] = row[col]
                        ref.child('status').child(timestamp_str.replace(":", "_").replace(" ", "_")).set(data_to_upload)

def upload_single_day_data(parent_dir, log_date):
    """Uploads data for a single day (or file, for Triton)."""
    fridge_type = get_fridge_type(PC_NAME)
    # Sanitize the log_date for Firebase *before* creating the reference.
    if fridge_type == "Oxford":
      sanitized_log_date = log_date.replace(" ", "_").replace(".", "_").split('_')[1]
      sanitized_log_date = f"{sanitized_log_date[:2]}-{sanitized_log_date[2:4]}-{sanitized_log_date[4:6]}"
    else: #bluefors
      sanitized_log_date = log_date
    ref = db.reference(f'/{PC_NAME}/{sanitized_log_date}')

    if fridge_type == "Oxford":
        log_reader = TritonLogReader
        log_file_path = os.path.join(parent_dir, log_date)  # log_date is filename
        if not log_file_path.endswith(".vcl") or not os.path.isfile(log_file_path):
            print(f"Invalid file or file not found: {log_file_path}")
            return

        print(f"Processing log file: {log_date}")

        try:
            reader = log_reader(log_file_path)
            data_df = reader.get_df()  # Get the entire DataFrame
            if not data_df.empty: #check if not empty
                upload_data_triton(data_df, log_date, ref) # Pass whole dataframe
            else:
                print("No data to upload.")

        except Exception as e:
            print(f"Error processing {log_date}: {e}")

    else:  # Assume BlueFors
        log_reader = BlueForsLogReader(parent_dir)
        log_date_path = os.path.join(parent_dir, log_date)
        if not os.path.isdir(log_date_path):
            print(f"Invalid log date directory: {log_date_path}")
            return

        print(f"Processing log date: {log_date}")

        for log_type in ["temperature", "pressure", "resistance", "flow_rate", "status"]:
            df = log_reader.get_logs(log_date, log_type)
            if df.empty:
                print(f"  No {log_type} data for {log_date}")
                continue

            print(f"  Uploading {log_type} data...")
            if log_type in ["temperature", "pressure", "resistance"]:
                for channel in range(1, 7):
                    channel_data = df[df['channel'] == channel]
                    if channel_data.empty:
                        continue

                    for _, row in channel_data.iterrows():
                        timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        value = row['value']
                        ref.child(log_type).child(f"CH{channel}").child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                            'timestamp': timestamp_str,
                            'value': float(value),
                            'channel': f"CH{channel}"
                        })
            elif log_type == "flow_rate":
                for _, row in df.iterrows():
                    timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    value = row['flow_rate']
                    ref.child('flow_rate').child(timestamp_str.replace(":", "_").replace(" ", "_")).set({
                        'timestamp': timestamp_str,
                        'value': float(value)
                    })
            elif log_type == "status":
                for _, row in df.iterrows():
                    timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    data_to_upload = {'timestamp': timestamp_str}
                    for col in df.columns:
                        if col != 'timestamp':
                            data_to_upload[col] = row[col]
                    ref.child('status').child(timestamp_str.replace(":", "_").replace(" ", "_")).set(data_to_upload)

def main():
    # Example Usage (choose one):

    # 1. Upload all data:
    # upload_all_data(LOGS_PARENT_DIRECTORY)

    # 2. Upload data for a single day (BlueFors):
    #upload_single_day_data(LOGS_PARENT_DIRECTORY, "22-07-21")

    # 3. Upload data for a single day (Oxford):
    upload_single_day_data(LOGS_PARENT_DIRECTORY, "log 240119 141920.vcl") #Pass filename for Oxford
    print("Data upload complete.")

if __name__ == "__main__":
    main()