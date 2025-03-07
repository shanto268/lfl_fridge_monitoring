import os

import pandas as pd


# BlueFors Log Reader
class BlueForsLogReader:
    def __init__(self, folder_path):
        self.folder_path = os.path.abspath(folder_path)

    def read_log_file(self, file_path, columns):
        """Reads a log file into a pandas DataFrame."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return pd.DataFrame()
        try:
            df = pd.read_csv(file_path, header=None, names=columns, delimiter=",")
            df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%y-%m-%d %H:%M:%S')
            return df.drop(columns=['date', 'time'])
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return pd.DataFrame()

    def get_logs(self, log_date, log_type):
        """Retrieve logs for the specified type."""
        folder = os.path.join(self.folder_path, log_date)
        if log_type in ["temperature", "pressure", "resistance"]:
            logs = []
            for channel in range(1, 7):
                file_name = f"CH{channel} {log_type[0].upper()} {log_date}.log"
                file_path = os.path.join(folder, file_name)
                df = self.read_log_file(file_path, ['date', 'time', 'value'])
                if not df.empty:
                    df['channel'] = channel
                    logs.append(df)
            return pd.concat(logs, ignore_index=True) if logs else pd.DataFrame()

        elif log_type == "status":
            file_name = f"Channels {log_date}.log"
            file_path = os.path.join(folder, file_name)
            try:
                # Read all lines from the file
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if not lines:
                        print(f"No data found in {file_path}")
                        return pd.DataFrame()

                # Extract the last row for headers
                last_row = lines[-1].strip().split(",")
                raw_headers = last_row[2::2]  # Extract every second element starting from index 2 (skipping values)
                headers = ['timestamp'] + raw_headers  # Add 'timestamp' as the first column

                # Prepare a list for data
                data = []

                # Iterate over each line and extract values
                for line in lines:
                    elements = line.strip().split(",")
                    timestamp = f"{elements[0]} {elements[1]}"  # Combine date and time
                    values = elements[2::2]  # Extract odd-numbered elements for values
                    data.append([timestamp] + values)

                # Create a DataFrame
                df = pd.DataFrame(data, columns=headers)

                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='%y-%m-%d %H:%M:%S')

                return df
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                return pd.DataFrame()
        elif log_type == "flowmeter":
            file_name = f"Flowmeter {log_date}.log"
            file_path = os.path.join(folder, file_name)
            return self.read_log_file(file_path, ['date', 'time', 'flow_rate'])

    def get_flowmeter(self, log_date):
        """Retrieve flowmeter logs for the specified date."""
        folder = os.path.join(self.folder_path, log_date)
        file_name = f"Flowmeter {log_date}.log"
        file_path = os.path.join(folder, file_name)
        return self.read_log_file(file_path, ['date', 'time', 'flow_rate'])

    def get_latest_entry(self, log_date):

            """Retrieves the latest entry for temperature, resistance, pressure, and flow rate."""

            latest_data = {}

            # Temperature, Resistance, and Pressure (for each channel)
            for log_type in ["temperature", "resistance", "pressure"]:
                df = self.get_logs(log_date, log_type)
                if not df.empty:
                    latest_data[log_type] = {}
                    for channel in range(1, 7):
                        channel_data = df[df['channel'] == channel]
                        if not channel_data.empty:
                            # Find the row with the maximum timestamp
                            latest_entry = channel_data.loc[channel_data['timestamp'].idxmax()]
                            latest_data[log_type][f'CH{channel}'] = {
                                'value': latest_entry['value'],
                                'timestamp': latest_entry['timestamp']
                            }

            # Flowmeter
            flowmeter_df = self.get_flowmeter(log_date)
            if not flowmeter_df.empty:
                latest_flow_entry = flowmeter_df.loc[flowmeter_df['timestamp'].idxmax()]
                latest_data['flow_rate'] = {
                    'value': latest_flow_entry['flow_rate'],
                    'timestamp': latest_flow_entry['timestamp']
                }

            return latest_data