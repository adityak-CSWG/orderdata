import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from google.cloud import secretmanager
from google.cloud import bigquery
import math
import json
import os

client = secretmanager.SecretManagerServiceClient()
response = client.access_secret_version(name='projects/998524737689/secrets/service-account-key')
service_account_secret = response.payload.data.decode("UTF-8")
service_account_key = json.loads(service_account_secret)

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

@st.cache_data(ttl=600)
def run_query():
    query_job = client.query(query)
    results = query_job.result()
    data = results.to_dataframe()
    return data

def main():
  df = run_query()
  df['ORDER_DATE'] = pd.to_datetime(df['ORDER_DATE'])
  df['num_orders'] = pd.to_numeric(df['num_orders'])

  #make list of all the unique order dates and warehouse addresses
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

  # Sort the DataFrame for better readability
  df = df.sort_values(by=['ORDER_DATE', 'warehouse_address']).reset_index(drop=True)

  # Sidebar for filters
  st.sidebar.header('Filters')

  # Date range picker
  start_date = st.sidebar.date_input('Start date', df['ORDER_DATE'].min().date())
  end_date = st.sidebar.date_input('End date', df['ORDER_DATE'].max().date())

  # Convert the date inputs to datetime format for comparison
  start_date = pd.to_datetime(start_date)
  end_date = pd.to_datetime(end_date)

  filtered_df = df[(df['ORDER_DATE'] >= start_date) & (df['ORDER_DATE'] <= end_date) & (df['trade_name'] != None)]

  # Warehouse selector
  warehouses = df['warehouse_address'].unique().tolist()
  selected_warehouses = st.sidebar.multiselect('Select Warehouses', warehouses, default=warehouses)
  filtered_df = filtered_df[filtered_df['warehouse_address'].isin(selected_warehouses)]

  # Main title
  st.title('Warehouse Orders Dashboard')

  # Summary statistics
  st.header('Summary Statistics')
  st.write(f"Total Orders: {filtered_df['num_orders'].sum()}")
  st.write(f"Average Orders per Day: {math.ceil(filtered_df.groupby('ORDER_DATE')['num_orders'].sum().mean())}")

  # Time series chart
  st.header('Time Series of Orders')
  time_series_chart = alt.Chart(filtered_df).mark_line().encode(
      x='ORDER_DATE:T',
      y='sum(num_orders)',
      color='warehouse_address:N',
  ).interactive()
  st.altair_chart(time_series_chart, use_container_width=True)

  # Bar chart of total orders per warehouse
  st.header('Total rders per Warehouse')
  total_orders_chart = alt.Chart(filtered_df).mark_bar().encode(
      x='warehouse_address:N',
      y='sum(num_orders):Q',
      color='warehouse_address:N',
      tooltip=['warehouse_address:N', 'sum(num_orders):Q']
  ).interactive()
  st.altair_chart(total_orders_chart, use_container_width=True)

  # Heatmap of daily order density
  st.header('Daily Order Density')
  heatmap_chart = alt.Chart(filtered_df).mark_rect().encode(
      x='ORDER_DATE:T',
      y='warehouse_address:N',
      color='sum(num_orders):Q',
      tooltip=['ORDER_DATE:T', 'warehouse_address:N', 'sum(num_orders):Q']
  ).interactive()
  st.altair_chart(heatmap_chart, use_container_width=True)

  # Pie chart of order proportions per warehouse
  st.header('Order Proportions per Warehouse')
  order_proportions = filtered_df.groupby('warehouse_address')['num_orders'].sum().reset_index()
  pie_chart = alt.Chart(order_proportions).mark_arc().encode(
      theta='num_orders:Q',
      color='warehouse_address:N',
      tooltip=['warehouse_address:N', 'num_orders:Q']
  ).interactive()
  st.altair_chart(pie_chart, use_container_width=True)

  # Data table
  st.header('Data Table')
  st.dataframe(filtered_df)

  # Download button
  st.header('Download Filtered Data')
  st.download_button(
      label="Download CSV",
      data=filtered_df.to_csv(index=False).encode('utf-8'),
      file_name='filtered_warehouse_orders.csv',
      mime='text/csv'
  )

main()