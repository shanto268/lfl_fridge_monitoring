import datetime
import os

import firebase_admin
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from firebase_admin import credentials, db

# --- Load Environment Variables and Initialize Firebase ---
load_dotenv()

# Construct Firebase credentials from env variables
firebase_creds = {
    "type":
    os.getenv("FIREBASE_TYPE"),
    "project_id":
    os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id":
    os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key":
    os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),  # Fix line breaks
    "client_email":
    os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id":
    os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri":
    os.getenv("FIREBASE_AUTH_URI"),
    "token_uri":
    os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url":
    os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url":
    os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
}

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv('DB_URL')
    })

PC_NAMES = ["sneezy", "dopey", "bashful"]  # Centralize PC names
DEFAULT_FRIDGE_TYPE = "BlueFors"

# --- Helper Functions ---


def get_fridge_type(pc_name: str) -> str:
    """Gets the fridge type for a given PC name."""
    if pc_name == "dopey":
        return "Oxford"
    else:
        return DEFAULT_FRIDGE_TYPE


def fetch_data_from_firebase(fridge_name: str,
                             log_date: str,
                             data_type: str = None,
                             channel_id: str = None):
    """Fetches data from Firebase, handling both BlueFors and Triton structures.

    Args:
        fridge_name: The name of the fridge (e.g., "sneezy").
        log_date: The date (YY-MM-DD) or Triton file name.
        data_type: "temperature", "pressure", "resistance", "flow_rate", "status", or None for all.
        channel_id:  Channel ID (e.g., "CH1") or None for all.
    """
    ref = db.reference(f'/{fridge_name}/{log_date}')

    try:
        if data_type == "status":
            data = ref.child("status").get()
        elif data_type == "flow_rate":
            data = ref.child("flow_rate").order_by_child('timestamp').get()
        elif data_type:  # temperature, pressure, resistance (BlueFors)
            if channel_id:
                data = ref.child(data_type).child(channel_id).order_by_child(
                    'timestamp').get()
            else:
                data = ref.child(data_type).order_by_child(
                    'timestamp').get()  # No channel, so get all
        else:  # Fetch all data (for Triton, or initial display)
            data = ref.get()
            if not data:  # Handle the Triton case
                if "vcl" in log_date or "log_" in log_date:  #check if triton
                    data = ref.order_by_child('timestamp').get()
        if not data:
            return None

        # Convert Firebase data (OrderedDict or list) to list of dictionaries
        if isinstance(data, dict):
            # Bluefors - when fetching all channels, data is a dict of channels
            if data_type in ("temperature", "pressure",
                             "resistance") and channel_id is None:
                data_list = []
                for channel, channel_data in data.items(
                ):  # Iterate through channels (CH1, CH2...)
                    if isinstance(channel_data, dict):
                        for entry_key, entry_value in channel_data.items(
                        ):  # Iterate through timestamp keys
                            if isinstance(entry_value, dict):
                                # entry_value is NOW a dictionary with 'timestamp', 'value', 'channel'
                                data_list.append(entry_value)

            else:  # Data is a single dictionary (status, flow_rate or Triton, or single channel)
                data_list = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        data_list.append(value)

            return data_list if data_list else None

        else:  # list - already in correct format
            return data

    except Exception as e:
        st.error(f"Error fetching data from Firebase: {e}")
        return None


def get_log_dates(fridge_name: str):
    """Gets all available log dates/filenames for a fridge."""
    ref = db.reference(f'/{fridge_name}')
    log_dates = ref.get()

    if not log_dates:
        return []  # Return an empty list if no data
    if isinstance(log_dates, dict):
        return sorted(log_dates.keys(),
                      key=lambda x: x.replace("_", ""),
                      reverse=True)  # Sort
    else:
        print(f"Unexpected data format for fridge {fridge_name}: {log_dates}")
        return []  # Unexpected format.


# --- Streamlit App ---


def main():
    st.set_page_config(page_title="Fridge Monitor", layout="wide")
    st.title("LFL Fridge Monitoring System")

    # Sidebar - Logo with link
    st.sidebar.image("lfl_logo.png", use_container_width=True)

    # Sidebar for selecting fridge and data type
    selected_fridge = st.sidebar.selectbox("Select Fridge", PC_NAMES)
    fridge_type = get_fridge_type(selected_fridge)

    # --- Date Selection ---
    log_dates = get_log_dates(selected_fridge)  # Get ALL available dates
    if not log_dates:
        st.warning("No data found for this fridge.")
        return

    selected_log_date = st.sidebar.selectbox("Select Date", log_dates)

    # --- Data Type and Channel Selection (Conditional) ---
    if fridge_type == "BlueFors":
        data_types = [
            "temperature", "pressure", "resistance", "flow_rate", "status"
        ]
        selected_data_type = st.sidebar.selectbox("Select Data Type",
                                                  data_types)
        selected_channel = None  # No longer needed, we will process all channels

        # Fetch data based on selection (no channel specified)
        data = fetch_data_from_firebase(selected_fridge, selected_log_date,
                                        selected_data_type, selected_channel)

        # --- Data Display and Plotting (BlueFors) ---
        if data:
            st.subheader(
                f"{selected_data_type.capitalize()} Data for {selected_fridge} ({selected_log_date})"
            )
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])

            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
            except (ValueError, KeyError) as e:
                st.error(
                    f"Error processing timestamps: {e}. Data might be incomplete or in an unexpected format."
                )
                st.dataframe(df)
                return

            # Plotting (BlueFors - All Channels)
            if selected_data_type != "status" and selected_data_type != "flow_rate":
                if 'channel' in df.columns and 'value' in df.columns:
                    try:
                        # No need to pivot if channel is already a column
                        fig = px.line(
                            df,
                            x='timestamp',
                            y='value',
                            color='channel',
                            title=
                            f"{selected_data_type.capitalize()} for All Channels"
                        )
                        fig.update_layout(xaxis_title="Timestamp",
                                          yaxis_title="Value")
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(
                            "Error plotting all channels. Check your data format"
                        )
                        st.write(e)
                        st.dataframe(df)

                else:
                    st.error(
                        "Data format does not support all-channel plotting.  Missing 'channel' or 'value' column"
                    )
                    st.dataframe(df)

            elif selected_data_type == "flow_rate":
                if 'value' in df.columns:
                    fig = px.line(df,
                                  x='timestamp',
                                  y='value',
                                  title=f'{selected_data_type} over Time')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(
                        "Data format does not support plotting. Missing 'value' column"
                    )
                    st.dataframe(df)
            else:
                st.dataframe(df)  #status case

        else:
            st.write("No data available for the selected options.")

    elif fridge_type == "Oxford":
        # Oxford-specific data fetching and display
        data = fetch_data_from_firebase(selected_fridge, selected_log_date)

        if data:
            st.subheader(f"Data for {selected_fridge} ({selected_log_date})")

            if isinstance(data, list):
                data_dict = data[0]  # Oxford data is now handled consistently
            elif isinstance(data, dict):
                data_dict = data
            else:
                st.write(data)
                return

            available_keys = list(data_dict.keys())
            available_keys_no_ts = [
                key for key in available_keys if key != 'timestamp'
            ]

            if not available_keys_no_ts:
                st.write("Only timestamp data available.")
                return

            selected_key = st.selectbox("Select Data to Display",
                                        available_keys_no_ts)

            display_data = []
            timestamps = []

            if isinstance(data, list):
                for item in data:
                    if selected_key in item:
                        display_data.append(item[selected_key])
                        timestamps.append(item.get('timestamp'))
            elif isinstance(data, dict):
                if selected_key in data:
                    display_data.append(data[selected_key])
                    timestamps.append(data.get('timestamp'))

            # Display and Plot the selected data (Oxford)
            if len(display_data) > 0:
                df = pd.DataFrame({
                    'Timestamp': timestamps,
                    selected_key: display_data
                })

                #Convert to datetime
                try:
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    df = df.sort_values('Timestamp')
                except (ValueError, KeyError) as e:
                    st.error(
                        f"Error processing timestamps: {e}. Data may be incomplete."
                    )
                    st.dataframe(df)  # Show even with errors.
                    return
                st.write(f"**{selected_key}:**")
                fig = px.line(df,
                              x='Timestamp',
                              y=selected_key,
                              title=f'{selected_key} over Time')
                st.plotly_chart(fig, use_container_width=True)
                # st.dataframe(df)  # Show as table
            else:
                st.write("Selected data not available in the fetched data.")

        else:
            st.write("No data available for this fridge.")


if __name__ == "__main__":
    main()
