import streamlit as st
import pandas as pd
import altair as alt
from google.oauth2 import service_account
from google.cloud import bigquery

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
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

df = run_query()

# Sidebar for filters
st.sidebar.header('Filters')

# Date range picker
start_date = st.sidebar.date_input('Start date', df['ORDER_DATE'].min().date())
end_date = st.sidebar.date_input('End date', df['ORDER_DATE'].max().date())

# Convert the date inputs to datetime format for comparison
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

filtered_df = df[(df['ORDER_DATE'] >= start_date) & (df['ORDER_DATE'] <= end_date)]

# Warehouse selector
warehouses = df['warehouse_address'].unique().tolist()
selected_warehouses = st.sidebar.multiselect('Select Warehouses', warehouses, default=warehouses)
filtered_df = filtered_df[filtered_df['warehouse_address'].isin(selected_warehouses)]

# Main title
st.title('Warehouse Orders Dashboard')

# Summary statistics
st.header('Summary Statistics')
st.write(f"Total Orders: {filtered_df['num_orders'].sum()}")
st.write(f"Average Orders per Day: {filtered_df.groupby('ORDER_DATE')['num_orders'].sum().mean():.2f}")

# Time series chart
st.header('Time Series of Orders')
time_series_chart = alt.Chart(filtered_df).mark_line(point=True).encode(
    x='ORDER_DATE:T',
    y='num_orders:Q',
    color='warehouse_address:N',
    tooltip=['ORDER_DATE:T', 'warehouse_address:N', 'num_orders:Q']
).interactive()
st.altair_chart(time_series_chart, use_container_width=True)

# Bar chart of total orders per warehouse
st.header('Total Orders per Warehouse')
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
