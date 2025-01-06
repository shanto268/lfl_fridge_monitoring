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
                with open(file_path, "r") as f:
                    headers = ['date', 'time'] + [f"status_{i}" for i in range(1, len(f.readline().split(",")) - 2)]
                df = pd.read_csv(file_path, header=None, names=headers, delimiter=",")
                df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%y-%m-%d %H:%M:%S')
                return df.drop(columns=['date', 'time'])
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                return pd.DataFrame()

        elif log_type == "flowmeter":
            file_name = f"Flowmeter {log_date}.log"
            file_path = os.path.join(folder, file_name)
            return self.read_log_file(file_path, ['date', 'time', 'flow_rate'])