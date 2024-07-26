import pandas as pd
import altair as alt
import streamlit as st
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

df['ORDER_DATE'] = pd.to_datetime(df['ORDER_DATE'])

# Ensure numeric conversion for 'num_orders'
df['num_orders'] = pd.to_numeric(df['num_orders'])

chart = alt.Chart(df).mark_line().encode(
    x='ORDER_DATE:T',
    y='num_orders:Q',
    color='warehouse_address:N',
    tooltip=['ORDER_DATE:T', 'warehouse_address:N', 'num_orders:Q']
).interactive()

# Display the chart in Streamlit
st.title('Warehouse Orders Time Series')
st.altair_chart(chart, use_container_width=True)
