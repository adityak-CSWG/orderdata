import streamlit as st
import pandas as pd
import altair as alt

# Load the cleaned CSV file
df = pd.read_csv('Cleaned_Warehouse_Orders_Data__New_.csv')

# Create a time series chart
chart = alt.Chart(df).mark_line(point=True).encode(
    x='date:T',
    y='num_orders:Q',
    color='warehouse_name:N',
    tooltip=['date:T', 'warehouse_name:N', 'num_orders:Q']
).interactive()

# Display the chart in Streamlit
st.title('Warehouse Orders Time Series')
st.altair_chart(chart, use_container_width=True)
