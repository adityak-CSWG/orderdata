import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from google.cloud import secretmanager
from google.cloud import bigquery
import math
import json
import google_crc32c
import os
from datetime import datetime, timedelta
import pytz

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './application_default_credentials.json'

def access_secret() -> secretmanager.AccessSecretVersionResponse:
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/998524737689/secrets/service-account-key/versions/latest"
    response = client.access_secret_version(request={"name": name})

    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        print("Data corruption detected.")
        return response

    payload = response.payload.data.decode("UTF-8")
    return payload

response = access_secret()
service_account_key = json.loads(response)

credentials = service_account.Credentials.from_service_account_info(
    service_account_key,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
client = bigquery.Client(credentials=credentials)

query = """
WITH FlattenedOrders AS (
  SELECT
    ORDER_DATE,
    o.trade_name,
    o.warehouse_address,
    o.num_orders
  FROM
    `gc-proj-devis-poc-6586.AppDev_Intern.customer-orders-2024`,
    UNNEST(CUSTOMER_ORDERS) AS o
)

SELECT
  ORDER_DATE,
  trade_name,
  warehouse_address,
  num_orders
FROM
  FlattenedOrders"""

timeZ_Ny = pytz.timezone('America/New_York') 
now = datetime.now(timeZ_Ny)
secs = int((timedelta(hours=24) - (now - now.replace(hour=8, minute=10, second=0))).total_seconds() % (24 * 3600))

@st.cache_data(ttl=secs)
def run_query():
    query_job = client.query(query)
    results = query_job.result()
    data = results.to_dataframe()
    return data

def load_data():
    df = run_query()
    df['ORDER_DATE'] = pd.to_datetime(df['ORDER_DATE'])
    df['num_orders'] = pd.to_numeric(df['num_orders'])

    order_dates = df['ORDER_DATE'].unique()
    warehouse_addresses = df['warehouse_address'].unique()

    missing_rows = []

  # Check for each combination of order_date and warehouse_address
    for order_date in order_dates:
      for warehouse_address in warehouse_addresses:
          # Filter for the specific combination
          if not ((df['ORDER_DATE'] == order_date) & (df['warehouse_address'] == warehouse_address)).any():
              missing_rows.append({
                  'ORDER_DATE': order_date,
                  'trade_name': 'None',
                  'warehouse_address': warehouse_address,
                  'num_orders': 0
              })

  # Append missing rows to the original DataFrame
    missing_df = pd.DataFrame(missing_rows)
    df = pd.concat([df, missing_df], ignore_index=True)
    return df

def filter_data(df, start_date, end_date, selected_warehouses):
    filtered_df = df[(df['ORDER_DATE'] >= start_date) & 
                     (df['ORDER_DATE'] <= end_date) & 
                     (df['warehouse_address'].isin(selected_warehouses)) & ((df['warehouse_address'] != '') & (df['trade_name'] != None) & (df['trade_name'] != 0))]
    return filtered_df

def update_filter_state():
    st.session_state.filters_changed = True

def main():
    if 'data' not in st.session_state or st.session_state.get('reset', False):
        st.session_state.data = load_data()
        st.session_state.start_date = st.session_state.data['ORDER_DATE'].min().date()
        st.session_state.end_date = st.session_state.data['ORDER_DATE'].max().date()
        st.session_state.selected_warehouses = [w for w in st.session_state.data['warehouse_address'].unique().tolist() if w != '']
        st.session_state.filters_changed = False
        st.session_state.reset = False

    if 'start_date' not in st.session_state:
        st.session_state.start_date = df['ORDER_DATE'].min().date()

    df = st.session_state.data

    # Sidebar for filters
    st.sidebar.header('Filters')

    start_date = st.sidebar.date_input('Start date', st.session_state.start_date, key='start_date', on_change=update_filter_state)
    end_date = st.sidebar.date_input('End date', st.session_state.end_date, key='end_date', on_change=update_filter_state)

    warehouses = df['warehouse_address'].unique().tolist()
    selected_warehouses = st.sidebar.multiselect('Select Warehouses', warehouses, default=st.session_state.selected_warehouses, key='selected_warehouses', on_change=update_filter_state)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        filter_button = st.button("Apply Filters", disabled=not st.session_state.filters_changed)
    with col2:
        reset_button = st.button("Reset Filters")

    if reset_button:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if filter_button:
        st.session_state.filters_changed = False
        st.session_state.filtered_df = filter_data(df, pd.to_datetime(start_date), pd.to_datetime(end_date), selected_warehouses)

    st.title('Warehouse Orders Dashboard')

    if 'filtered_df' not in st.session_state:
        st.session_state.filtered_df = filter_data(df, pd.to_datetime(st.session_state.start_date), pd.to_datetime(st.session_state.end_date), st.session_state.selected_warehouses)

    display_summary_statistics(st.session_state.filtered_df)
    display_charts(st.session_state.filtered_df)
    display_data_table(st.session_state.filtered_df)

def display_summary_statistics(filtered_df):
    st.header('Summary Statistics')
    st.write(f"Total Orders: {filtered_df['num_orders'].sum()}")
    st.write(f"Average Orders per Day: {math.ceil(filtered_df.groupby('ORDER_DATE')['num_orders'].sum().mean())}")

def display_charts(filtered_df):
    st.header('Time Series of Orders')
    time_series_chart = alt.Chart(filtered_df).mark_line().encode(
        x='ORDER_DATE:T',
        y='sum(num_orders)',
        color='warehouse_address:N',
    ).interactive()
    st.altair_chart(time_series_chart, use_container_width=True)

    st.header('Total Orders per Warehouse')
    total_orders_chart = alt.Chart(filtered_df).mark_bar().encode(
        x='warehouse_address:N',
        y='sum(num_orders):Q',
        color='warehouse_address:N',
        tooltip=['warehouse_address:N', 'sum(num_orders):Q']
    ).interactive()
    st.altair_chart(total_orders_chart, use_container_width=True)

    st.header('Daily Order Density')
    heatmap_chart = alt.Chart(filtered_df).mark_rect().encode(
        x='ORDER_DATE:T',
        y='warehouse_address:N',
        color='sum(num_orders):Q',
        tooltip=['ORDER_DATE:T', 'warehouse_address:N', 'sum(num_orders):Q']
    ).interactive()
    st.altair_chart(heatmap_chart, use_container_width=True)

    st.header('Order Proportions per Warehouse')
    order_proportions = filtered_df.groupby('warehouse_address')['num_orders'].sum().reset_index()
    pie_chart = alt.Chart(order_proportions).mark_arc().encode(
        theta='num_orders:Q',
        color='warehouse_address:N',
        tooltip=['warehouse_address:N', 'num_orders:Q']
    ).interactive()
    st.altair_chart(pie_chart, use_container_width=True)

def display_data_table(filtered_df):
    st.header('Data Table')
    st.dataframe(filtered_df)

    st.header('Download Filtered Data')
    st.download_button(
        label="Download CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_warehouse_orders.csv',
        mime='text/csv'
    )

if __name__ == "__main__":
    main()
