import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import calendar


def clean_data(df):
    """Clean the dataframe by using correct column names and data types"""
    df.columns = df.iloc[1]
    df = df.iloc[2:].reset_index(drop=True)

    df['Fees Paid Date'] = pd.to_datetime(df['Fees Paid Date'], errors='coerce')

    df['Payment Type'] = df['Payment Details'].fillna('OTHER')
    df['Payment Type'] = df['Payment Type'].apply(
        lambda x: 'CASH' if str(x).upper() == 'CASH'
        else ('ONLINE' if str(x).upper() == 'ONLINE' else 'OTHER')
    )

    df['Paid Amount'] = pd.to_numeric(df['Paid Amount'], errors='coerce').fillna(0)
    return df


def get_data_by_date(df, selected_date):
    return df[df['Fees Paid Date'].dt.date == selected_date]


def create_time_summaries(df):
    """Create weekly and monthly summaries"""
    # Monthly Summary
    monthly_summary = df.groupby([
        df['Fees Paid Date'].dt.year,
        df['Fees Paid Date'].dt.month,
        'Payment Type'
    ])['Paid Amount'].sum().reset_index()

    monthly_summary['Period'] = monthly_summary.apply(
        lambda x: f"{calendar.month_name[int(x['Month'])]} {int(x['Year'])}",
        axis=1
    )

    # Weekly Summary
    df['Week'] = df['Fees Paid Date'].dt.isocalendar().week
    weekly_summary = df.groupby([
        df['Fees Paid Date'].dt.year,
        'Week',
        'Payment Type'
    ])['Paid Amount'].sum().reset_index()

    weekly_summary['Period'] = weekly_summary.apply(
        lambda x: f"Week {int(x['Week'])}, {int(x['Year'])}",
        axis=1
    )

    return monthly_summary, weekly_summary


def display_payment_summary_table(df, date=None):
    """Display payment type summary table"""
    if date:
        df = df[df['Fees Paid Date'].dt.date == date]

    summary = df.groupby('Payment Type')['Paid Amount'].agg(['sum', 'count']).reset_index()
    summary.columns = ['Payment Type', 'Total Amount', 'Number of Transactions']

    # Style the dataframe
    st.markdown("""
    <style>
    .payment-summary {
        font-size: 1.2em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="payment-summary">Payment Summary</p>', unsafe_allow_html=True)
    st.dataframe(summary.style.format({
        'Total Amount': '₹{:,.2f}',
        'Number of Transactions': '{:,.0f}'
    }), height=150)


def main():
    st.set_page_config(page_title="School Fees Analytics", layout="wide")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Data Export", "Daily Analytics", "Advanced Analytics"]
    )

    # File upload in sidebar
    uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=['xlsx', 'xls'])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        df = clean_data(df)

        available_dates = sorted(df['Fees Paid Date'].dt.date.unique())

        st.title("School Fees Analytics Dashboard")

        if page == "Data Export":
            st.header("Export Data by Date")

            # Style the date picker and download button
            st.markdown("""
                <style>
                .stButton>button {
                    background-color: #4CAF50;
                    color: white;
                    padding: 15px 32px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 4px;
                    border: none;
                }
                </style>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])
            with col1:
                selected_date = st.date_input(
                    "Select Date",
                    min_value=min(available_dates) if available_dates else None,
                    max_value=max(available_dates) if available_dates else None,
                    value=min(available_dates) if available_dates else None
                )

            if selected_date:
                filtered_df = get_data_by_date(df, selected_date)

                if not filtered_df.empty:
                    display_payment_summary_table(filtered_df, selected_date)
                    st.write(f"Found {len(filtered_df)} records for {selected_date}")
                    st.dataframe(filtered_df)

                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        filtered_df.to_excel(writer, index=False)

                    with col2:
                        st.download_button(
                            label="📥 Download Excel",
                            data=buffer.getvalue(),
                            file_name=f"school_fees_data_{selected_date}.xlsx",
                            mime="application/vnd.ms-excel"
                        )

        elif page == "Daily Analytics":
            st.header("Daily Payment Analytics")
            analytics_date = st.date_input(
                "Select Date for Analytics",
                min_value=min(available_dates) if available_dates else None,
                max_value=max(available_dates) if available_dates else None,
                value=min(available_dates) if available_dates else None
            )

            if analytics_date:
                daily_data = get_data_by_date(df, analytics_date)
                if not daily_data.empty:
                    display_payment_summary_table(daily_data, analytics_date)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Paid Amount", f"₹{daily_data['Paid Amount'].sum():,.2f}")
                    with col2:
                        st.metric("Total Transactions", len(daily_data))

                    fig = px.pie(daily_data.groupby('Payment Type')['Paid Amount'].sum().reset_index(),
                                 values='Paid Amount', names='Payment Type',
                                 title='Payment Type Distribution')
                    st.plotly_chart(fig)

        elif page == "Time-based Analysis":
            st.header("Time-based Analysis")

            monthly_summary, weekly_summary = create_time_summaries(df)

            # Monthly view
            st.subheader("Monthly Summary")
            monthly_pivot = pd.pivot_table(
                monthly_summary,
                values='Paid Amount',
                index='Period',
                columns='Payment Type',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            monthly_pivot['Total'] = monthly_pivot[['CASH', 'ONLINE', 'OTHER']].sum(axis=1)
            st.dataframe(monthly_pivot.style.format({
                'CASH': '₹{:,.2f}',
                'ONLINE': '₹{:,.2f}',
                'OTHER': '₹{:,.2f}',
                'Total': '₹{:,.2f}'
            }))

            # Weekly view
            st.subheader("Weekly Summary")
            weekly_pivot = pd.pivot_table(
                weekly_summary,
                values='Paid Amount',
                index='Period',
                columns='Payment Type',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            weekly_pivot['Total'] = weekly_pivot[['CASH', 'ONLINE', 'OTHER']].sum(axis=1)
            st.dataframe(weekly_pivot.style.format({
                'CASH': '₹{:,.2f}',
                'ONLINE': '₹{:,.2f}',
                'OTHER': '₹{:,.2f}',
                'Total': '₹{:,.2f}'
            }))

        elif page == "Advanced Analytics":
            st.header("Advanced Analytics")

            # Overall statistics
            total_collection = df['Paid Amount'].sum()
            total_transactions = len(df)
            unique_dates = df['Fees Paid Date'].dt.date.nunique()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Collection", f"₹{total_collection:,.2f}")
            col2.metric("Total Transactions", f"{total_transactions:,}")
            col3.metric("Active Days", f"{unique_dates:,}")




if __name__ == "__main__":
    main()