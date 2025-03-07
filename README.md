# BlueFors Data Logger and Monitor

This project monitors a BlueFors dilution refrigerator, logging data to a Firebase Realtime Database.

## Features

- **Real-Time Monitoring:** Continuously updates Firebase with the latest log data.

## Setup

### 1. Prerequisites

- Python 3.11+
- A Google Cloud Platform (GCP) project with Firebase enabled.
- A Firebase Realtime Database instance.

### 2. Google Cloud & Firebase Setup

1.  **Create a GCP Project:** If you don't have one, create a project in the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Enable Firebase:** In your GCP project, navigate to Firebase and enable it.
3.  **Create a Realtime Database:** Within Firebase, create a Realtime Database instance. Note the database URL (e.g., `https://<your-project-id>.firebaseio.com/`).
4.  **Create a Service Account:**
    - Go to "Project settings" (gear icon) in the Firebase console.
    - Select the "Service accounts" tab.
    - Click "Generate new private key". This downloads a JSON file (e.g., `sneezy.json`). **Keep this file secure!** Place it in the project's root directory.
5.  **Set Firebase Rules:** In the Firebase console, go to "Realtime Database" -> "Rules" and paste the following, replacing the key entries.

    ```json
    {
      "rules": {
        "BlueFors_PC": {
          // Setup for BlueFors System
          ".read": true,
          ".write": "auth.uid === 'PC_NAME'", // Replace 'PC_NAME' with the actual UID
          "$log_date": {
            "flow_rate": { ".indexOn": ["timestamp"] },
            "temperature": {
              "CH1": { ".indexOn": ["timestamp"] },
              "CH2": { ".indexOn": ["timestamp"] },
              "CH3": { ".indexOn": ["timestamp"] },
              "CH4": { ".indexOn": ["timestamp"] },
              "CH5": { ".indexOn": ["timestamp"] },
              "CH6": { ".indexOn": ["timestamp"] }
            },
            "resistance": {
              "CH1": { ".indexOn": ["timestamp"] },
              "CH2": { ".indexOn": ["timestamp"] },
              "CH3": { ".indexOn": ["timestamp"] },
              "CH4": { ".indexOn": ["timestamp"] },
              "CH5": { ".indexOn": ["timestamp"] },
              "CH6": { ".indexOn": ["timestamp"] }
            },
            "pressure": {
              "CH1": { ".indexOn": ["timestamp"] },
              "CH2": { ".indexOn": ["timestamp"] },
              "CH3": { ".indexOn": ["timestamp"] },
              "CH4": { ".indexOn": ["timestamp"] },
              "CH5": { ".indexOn": ["timestamp"] },
              "CH6": { ".indexOn": ["timestamp"] }
            }
          }
        },
        "OXFORD_PC": {
          // Setup for Oxford Triton Systems
          ".read": true,
          ".write": "auth.uid === 'PC_NAME'",
          "$log_date": {
            ".indexOn": ["timestamp"],
            "$data": {
              ".write": "newData.parent().child('timestamp').exists() && newData.val() != 0"
            }
          }
        }
      }
    }
    ```

    **Repeat this structure for each PC**, changing `"PC_NAME"` and the corresponding `auth.uid` in the `.write` rule.

### 3. Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    conda create -n fridge_env python=3.9 -y
    conda activate fridge_env
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    (`requirements.txt` should contain: `firebase-admin`, `pandas`, `python-dotenv`)

### 4. Configuration

1.  Create a `.env` file in the project's root directory:

    ```
    DB_URL='https://<YOUR_DATABASE_URL>.firebaseio.com/'
    PC_NAME='pc_name'
    CRED_FILE="credfilename.json"
    FRIDGE_TYPE="yourfridgetype" # Oxford or Bluefors
    LOGFILE_DIR="path/to/your/log/files"
    ```

    Replace placeholders with your actual values.

2.  Ensure your log files are in a `logs` subdirectory, organized by date (e.g., `logs/22-07-20/CH1 T 22-07-20.log`).

### 5. Usage

Run the real-time monitor:

```bash
python log_to_db.py
```

To run in the background:

```bash
nohup python log_to_db.py &
```

**Important:** Set the `PC_NAME` environment variable correctly on each machine running the script.

## Log File Format

### BlueFors System:

Log files must be in the `logs` directory and follow these naming conventions (this is by default what it should be):

- Temperature: `CHX T YY-MM-DD.log`
- Pressure: `CHX P YY-MM-DD.log`
- Resistance: `CHX R YY-MM-DD.log`
- Status: `Channels YY-MM-DD.log`
- Flow Rate: `Flowmeter YY-MM-DD.log`

### Oxford System:

Point to the path with the `.vcl` files.

## Security

**Implement Firebase Authentication:** The provided rules are placeholders. You _must_ implement Firebase Authentication to secure your database and restrict write access to authorized users/devices. Refer to the Firebase documentation for details.
