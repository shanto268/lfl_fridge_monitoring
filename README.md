# LFL Fridge Data Feeding System

This repository contains code to push dilution fridge system data (both BlueFors and Oxford Systems) to a Firebase Realtime Database and a Streamlit web application to visualize the data.

## Features

- **Real-Time Monitoring:** Continuously updates Firebase with the latest log data.
- **Data Upload:** Supports both continuous monitoring (`log_to_db.py`) and historical data upload (`upload_all_logs.py`, `upload_single_day_data.py`).
- **Fridge Type Support:** Handles both BlueFors and Oxford (Triton) log file formats.
- **Streamlit Web App:** Provides a user-friendly interface to view the data, with interactive Plotly charts.
- **Firebase Integration:** Uses Firebase Realtime Database for data storage and retrieval.

## Setup

### 1. Prerequisites

- Python 3.7+
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
5.  **Set Firebase Rules:** In the Firebase console, go to "Realtime Database" -> "Rules". _Replace_ the existing rules with the following JSON:

    ```json
    {
      "rules": {
        "$pcName": {
          "$logDate": {
            ".indexOn": ["timestamp"],
            "temperature": {
              "$channel": {
                ".indexOn": ["timestamp"]
              }
            },
            "pressure": {
              "$channel": {
                ".indexOn": ["timestamp"]
              }
            },
            "resistance": {
              "$channel": {
                ".indexOn": ["timestamp"]
              }
            },
            "flow_rate": {
              ".indexOn": ["timestamp"]
            },
            "status": {
              ".indexOn": ["timestamp"]
            }
          }
        },
        ".read": "true", // Replace with appropriate security rules
        ".write": "true" // Replace with appropriate security rules
      }
    }
    ```

    **Important:** This rule set uses wildcards (`$pcName`, `$logDate`, `$channel`) to apply to all your fridges and dates. It includes indexes on the `timestamp` field for efficient querying. **You must replace `.read: true` and `.write: true` with appropriate security rules for production use.** See the "Security" section below. This rule set supports _both_ BlueFors and Oxford data structures. The Oxford-specific write rule (preventing zero values) is no longer needed, as the filtering is now done in the Python code.

### 3. Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    conda create -n fridge_env python=3.9 -y  # Or your preferred method
    conda activate fridge_env
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    (`requirements.txt` should contain: `firebase-admin`, `pandas`, `python-dotenv`, `plotly`, `streamlit`)

### 4. Configuration

1.  Create a `.env` file in the project's root directory:

    ```
    DB_URL=https://<YOUR_DATABASE_URL>[.firebaseio.com/](https://www.google.com/search?q=https://.firebaseio.com/)
    PC_NAME=sneezy  # Change to dopey, bashful, or test, as appropriate for each machine.
    CRED_FILE=sneezy.json  # Path to your service account key file.
    FRIDGE_TYPE=BlueFors  #  Oxford or BlueFors.  Set per-machine.
    LOGFILE_DIR=logs # Optional.  Defaults to "logs".  Path to log files.
    ```

    Replace placeholders with your actual values. `PC_NAME` and `FRIDGE_TYPE` should be set appropriately for _each machine_ running the `log_to_db.py` script.

2.  Ensure your log files are in the directory specified by `LOGFILE_DIR` (defaults to `logs`):
    - **BlueFors:** Organized by date (e.g., `logs/22-07-20/CH1 T 22-07-20.log`).
    - **Oxford/Triton:** `.vcl` files directly in the `logs` directory (e.g., `logs/log 240119 141920.vcl`).

**For Webapp Deployment:**

1. **Store Firebase Credentials Securely**  
   Streamlit uses `secrets.toml` for storing private keys. Create a `secrets.toml` file in the `.streamlit/` directory:

   ```
   .streamlit/secrets.toml
   ```

   **Example:**
   ```toml
   [firebase]
   FIREBASE_TYPE = "service_account"
   FIREBASE_PROJECT_ID = "your-project-id"
   FIREBASE_PRIVATE_KEY_ID = "your-private-key-id"
   FIREBASE_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nABC123...\n-----END PRIVATE KEY-----"
   FIREBASE_CLIENT_EMAIL = "your-client-email@your-project.iam.gserviceaccount.com"
   FIREBASE_CLIENT_ID = "your-client-id"
   FIREBASE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
   FIREBASE_TOKEN_URI = "https://oauth2.googleapis.com/token"
   FIREBASE_AUTH_PROVIDER_X509_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
   FIREBASE_CLIENT_X509_CERT_URL = "https://www.googleapis.com/robot/v1/metadata/x509/your-client-email@your-project.iam.gserviceaccount.com"
   DB_URL = "https://your-database.firebaseio.com/"
   ```

   **Ensure:**  
   - The **private key** is formatted correctly, preserving `\n` for line breaks.
   - The `.streamlit/secrets.toml` file is **never committed** to Git. Add it to `.gitignore`:
     ```
     .streamlit/secrets.toml
     ```

This replaces `.env` files and ensures **secure storage** for Firebase credentials.

---

This update ensures better security and seamless integration with Streamlit. Let me know if you need further refinements! 🚀

## Programs

### 1. Real-Time Monitor (`log_to_db.py`)

**Purpose:** Continuously monitors log files and uploads new data to Firebase in real-time.

**Usage:**

```bash
python log_to_db.py
```

**To Run as Background Process:**

```bash
nohup python log_to_db.py &
```

**Description:**

- Detects the fridge type (BlueFors or Oxford) based on the `FRIDGE_TYPE` environment variable.
- **BlueFors:** Monitors the `logs` directory for new date directories and files within those directories.
- **Oxford:** Monitors the `logs` directory for new `.vcl` files.
- Uploads the latest data to Firebase, using the appropriate data structure for each fridge type.
- Avoids uploading duplicate data.
- Runs continuously, checking for updates every 60 seconds.

### 2. Upload Historical Data (`upload_all_logs.py`)

**Purpose:** Uploads _all_ historical log data from a specified parent directory to Firebase, or uploads data for a _single_ day (BlueFors) or a single file (Oxford). Useful for initial data population or re-uploading specific data.

**Usage:**

```bash
python upload_all_logs.py
```

**Description:**

- Processes all log files (BlueFors or Oxford) within the directory specified by `LOGS_PARENT_DIRECTORY` in `.env` (or the default 'logs').
- For BlueFors, you can select option 2 to upload data for a specific date.
- For Oxford, select option 3 to upload a specific file by entering the filename (including the .vcl).

### 4. Streamlit Web App (`app.py`) - _VIEWING_ the data

**Purpose:** Provides a web-based interface to view the data stored in Firebase.

**Usage:**

```bash
streamlit run app.py
```

**Description:**

- **Fridge Selection:** Select the fridge you want to view data for.
- **Date Selection:** Select the date (or log file, for Oxford) you want to view.
- **Data Type Selection (BlueFors):** Choose the data type (temperature, pressure, resistance, flow rate, status). All channels are plotted on a single interactive chart.
- **Data Field Selection (Oxford):** Choose which data field to display from the available data.
- **Interactive Plots:** Uses Plotly for interactive charts.
- **Data Table:** Displays the raw data in a table format.

## Log File Formats

- **BlueFors:**
  - Temperature: `CHX T YY-MM-DD.log`
  - Pressure: `CHX P YY-MM-DD.log`
  - Resistance: `CHX R YY-MM-DD.log`
  - Status: `Channels YY-MM-DD.log`
  - Flow Rate: `Flowmeter YY-MM-DD.log`
- **Oxford/Triton:** `.vcl` files (e.g., `log 240119 141920.vcl`). Place these directly in the `logs` directory.

## Security

**Implement Firebase Authentication:** The provided Firebase rules are _placeholders only_. You **must** implement Firebase Authentication to properly secure your database. This involves:

1.  **Setting up Authentication:** Enable authentication methods in your Firebase project (e.g., email/password, Google Sign-In).
2.  **Modifying Rules:** Change the `.read` and `.write` rules to use `auth.uid` to restrict access based on user authentication. Refer to the Firebase documentation for details on how to write secure rules. For example:

    ```json
      ".read": "auth != null",
      ".write": "auth.uid === 'your_admin_uid'" // Or a more complex rule
    ```
