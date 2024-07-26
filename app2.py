import streamlit as st
import pandas as pd
import altair as alt

# Load the cleaned CSV file
df = pd.read_csv('Cleaned_Warehouse_Orders_Data__New_.csv')

# Convert 'date' column to datetime
df['date'] = pd.to_datetime(df['date'])

# Sidebar for filters
st.sidebar.header('Filters')

# Date range picker
start_date = st.sidebar.date_input('Start date', df['date'].min().date())
end_date = st.sidebar.date_input('End date', df['date'].max().date())

# Convert the date inputs to datetime format for comparison
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

# Warehouse selector
warehouses = df['warehouse_name'].unique().tolist()
selected_warehouses = st.sidebar.multiselect('Select Warehouses', warehouses, default=warehouses)
filtered_df = filtered_df[filtered_df['warehouse_name'].isin(selected_warehouses)]

# Main title
st.title('Warehouse Orders Dashboard')

# Summary statistics
st.header('Summary Statistics')
st.write(f"Total Orders: {filtered_df['num_orders'].sum()}")
st.write(f"Average Orders per Day: {filtered_df.groupby('date')['num_orders'].sum().mean():.2f}")

# Time series chart
st.header('Time Series of Orders')
time_series_chart = alt.Chart(filtered_df).mark_line(point=True).encode(
    x='date:T',
    y='num_orders:Q',
    color='warehouse_name:N',
    tooltip=['date:T', 'warehouse_name:N', 'num_orders:Q']
).interactive()
st.altair_chart(time_series_chart, use_container_width=True)

# Bar chart of total orders per warehouse
st.header('Total Orders per Warehouse')
total_orders_chart = alt.Chart(filtered_df).mark_bar().encode(
    x='warehouse_name:N',
    y='sum(num_orders):Q',
    color='warehouse_name:N',
    tooltip=['warehouse_name:N', 'sum(num_orders):Q']
).interactive()
st.altair_chart(total_orders_chart, use_container_width=True)

# Heatmap of daily order density
st.header('Daily Order Density')
heatmap_chart = alt.Chart(filtered_df).mark_rect().encode(
    x='date:T',
    y='warehouse_name:N',
    color='sum(num_orders):Q',
    tooltip=['date:T', 'warehouse_name:N', 'sum(num_orders):Q']
).interactive()
st.altair_chart(heatmap_chart, use_container_width=True)

# Pie chart of order proportions per warehouse
st.header('Order Proportions per Warehouse')
order_proportions = filtered_df.groupby('warehouse_name')['num_orders'].sum().reset_index()
pie_chart = alt.Chart(order_proportions).mark_arc().encode(
    theta='num_orders:Q',
    color='warehouse_name:N',
    tooltip=['warehouse_name:N', 'num_orders:Q']
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
