import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(
    page_title="Retail Sales Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished UI
st.markdown("""
<style>
.reportview-container {
    background: #f8f9fa;
}
div[data-testid="stMetricValue"] {
    font-size: 26px;
    font-weight: 700;
    color: #1E3A8A;
}
div[data-testid="stMetricLabel"] {
    font-size: 14px;
    font-weight: 600;
    color: #4B5563;
}
.insight-card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 8px;
    border-left: 5px solid #2563EB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 15px;
}
.insight-card-warning {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 8px;
    border-left: 5px solid #DC2626;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 15px;
}
.insight-title {
    font-size: 16px;
    font-weight: 700;
    color: #1F2937;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Retail Sales Intelligence Dashboard")
st.markdown("Analyze validated retail store performance, product sales trends, stock levels, and targets.")

# Data Cleaning and Validation Engine
def clean_and_validate_data(df_sales_raw):
    df = df_sales_raw.copy()
    
    # 1. Parse dates and drop completely unparseable rows
    df['week_start_date'] = pd.to_datetime(df['week_start_date'], errors='coerce')
    df = df.dropna(subset=['week_start_date'])
    df['week_start_date'] = df['week_start_date'].dt.strftime('%Y-%m-%d')
    
    # 2. Force numeric type compliance across all quantitative fields
    numeric_cols = ['footfall', 'transactions', 'units_sold', 'gross_sales', 'discount_amount', 
                    'net_sales', 'sales_target', 'inventory_on_hand', 'stockouts', 'returns_amount',
                    'customer_rating', 'marketing_spend']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # 3. Apply Accounting Identity Restorations to correct text anomalies and NaNs
    mask_gross_missing = df['gross_sales'].isna() & df['net_sales'].notna() & df['discount_amount'].notna()
    df.loc[mask_gross_missing, 'gross_sales'] = df.loc[mask_gross_missing, 'net_sales'] + df.loc[mask_gross_missing, 'discount_amount']
    
    mask_net_missing = df['net_sales'].isna() & df['gross_sales'].notna() & df['discount_amount'].notna()
    df.loc[mask_net_missing, 'net_sales'] = df.loc[mask_net_missing, 'gross_sales'] - df.loc[mask_net_missing, 'discount_amount']
    
    mask_neg_discount = (df['discount_amount'] < 0) & df['gross_sales'].notna() & df['net_sales'].notna()
    df.loc[mask_neg_discount, 'discount_amount'] = df.loc[mask_neg_discount, 'gross_sales'] - df.loc[mask_neg_discount, 'net_sales']
    
    # 4. Enforce structural boundary constraints
    df['discount_amount'] = df['discount_amount'].clip(lower=0).fillna(0.0)
    df['stockouts'] = df['stockouts'].clip(lower=0).fillna(0.0)
    
    # Fill any remaining unresolvable numeric NaN gaps with 0.0
    for col in numeric_cols:
        df[col] = df[col].fillna(0.0)
        
    return df

# Helper to generate mock clean data if no file is uploaded
def generate_mock_data():
    np.random.seed(42)
    start_date = datetime(2026, 1, 5)
    weeks = [start_date + timedelta(weeks=i) for i in range(12)]
    categories = ["Grocery", "Apparel", "Electronics", "Home", "Beauty"]
    stores = [{"store_id": f"ST-{i:03d}", "store_name": f"Store {i}", "region": "North", "city": "City A", "store_format": "Mall"} for i in range(1, 6)]
    
    weekly_sales_data = []
    for week in weeks:
        week_str = week.strftime('%Y-%m-%d')
        for s in stores:
            for cat in categories:
                footfall = int(np.random.normal(2000, 400))
                transactions = int(footfall * 0.25)
                net_sales = float(transactions * 50)
                weekly_sales_data.append({
                    "week_start_date": week_str, "region": s["region"], "store_id": s["store_id"],
                    "store_name": s["store_name"], "city": s["city"], "store_format": s["store_format"],
                    "product_category": cat, "footfall": footfall, "transactions": transactions,
                    "units_sold": transactions * 2, "gross_sales": net_sales * 1.1, "discount_amount": net_sales * 0.1,
                    "net_sales": net_sales, "sales_target": net_sales * 0.95, "inventory_on_hand": 500,
                    "stockouts": 2, "returns_amount": net_sales * 0.02, "customer_rating": 4.2, "marketing_spend": 500.0
                })
    return pd.DataFrame(weekly_sales_data), pd.DataFrame(stores)

st.sidebar.header("📁 Data Source Integration")
use_demo = st.sidebar.checkbox("Use Demo Sales Dataset", value=True)

uploaded_sales = st.sidebar.file_uploader("Upload Weekly Sales Data (.xlsx)", type=["xlsx"])
uploaded_master = st.sidebar.file_uploader("Upload Store Master Data (.xlsx)", type=["xlsx"])

df_sales, df_master = None, None

if uploaded_sales is not None and uploaded_master is not None:
    try:
        raw_sales = pd.read_excel(uploaded_sales)
        df_master = pd.read_excel(uploaded_master)
        df_sales = clean_and_validate_data(raw_sales)
        st.sidebar.success("Successfully loaded and validated data!")
    except Exception as e:
        st.sidebar.error(f"Error loading files: {str(e)}")
elif use_demo:
    df_sales, df_master = generate_mock_data()
    st.sidebar.info("Using clean simulated dataset for display.")

if df_sales is not None and df_master is not None:
    df_sales = df_sales.copy()
    df_master = df_master.copy()
    
    redundant_columns = ['store_name', 'region', 'city', 'store_format']
    df_master_clean = df_master.drop(columns=[col for col in redundant_columns if col in df_master.columns], errors='ignore')
    
    try:
        merged_df = pd.merge(df_sales, df_master_clean, on='store_id', how='inner')
    except Exception as e:
        st.error(f"Data merge failure: Common key 'store_id' missing. Details: {str(e)}")
        st.stop()

    st.sidebar.header("🎯 Dashboard Filters")
    weeks = sorted(merged_df['week_start_date'].unique())
    regions = sorted(merged_df['region'].unique())
    stores_list = sorted(merged_df['store_name'].unique())
    cities = sorted(merged_df['city'].unique())
    formats = sorted(merged_df['store_format'].unique())
    categories = sorted(merged_df['product_category'].unique())
    
    selected_weeks = st.sidebar.multiselect("Select Week(s)", options=weeks, default=weeks)
    selected_regions = st.sidebar.multiselect("Select Region(s)", options=regions, default=regions)
    selected_stores = st.sidebar.multiselect("Select Store(s)", options=stores_list, default=stores_list)
    selected_cities = st.sidebar.multiselect("Select City/Cities", options=cities, default=cities)
    selected_formats = st.sidebar.multiselect("Select Store Format(s)", options=formats, default=formats)
    selected_categories = st.sidebar.multiselect("Select Product Category/Categories", options=categories, default=categories)
    
    filtered_df = merged_df[
        (merged_df['week_start_date'].isin(selected_weeks if selected_weeks else weeks)) &
        (merged_df['region'].isin(selected_regions if selected_regions else regions)) &
        (merged_df['store_name'].isin(selected_stores if selected_stores else stores_list)) &
        (merged_df['city'].isin(selected_cities if selected_cities else cities)) &
        (merged_df['store_format'].isin(selected_formats if selected_formats else formats)) &
        (merged_df['product_category'].isin(selected_categories if selected_categories else categories))
    ]
    
    # Financial Aggregations
    total_net_sales = filtered_df['net_sales'].sum()
    total_sales_target = filtered_df['sales_target'].sum()
    total_transactions = filtered_df['transactions'].sum()
    total_returns = filtered_df['returns_amount'].sum()
    total_discounts = filtered_df['discount_amount'].sum()
    total_gross_sales = filtered_df['gross_sales'].sum()
    total_footfall = filtered_df['footfall'].sum()
    
    target_achievement = (total_net_sales / total_sales_target * 100) if total_sales_target > 0 else 0.0
    atv = (total_net_sales / total_transactions) if total_transactions > 0 else 0.0
    return_rate = (total_returns / total_net_sales * 100) if total_net_sales > 0 else 0.0
    discount_rate = (total_discounts / total_gross_sales * 100) if total_gross_sales > 0 else 0.0
    conversion_rate = (total_transactions / total_footfall * 100) if total_footfall > 0 else 0.0

    # Spacious Double-Row Metric Layout (Solves Truncation)
    st.subheader("📌 Key Performance Indicators (KPIs)")
    
    row1_kpis = st.columns(3)
    row1_kpis[0].metric("Net Sales", f"${total_net_sales:,.2f}")
    row1_kpis[1].metric("Target Achievement", f"{target_achievement:.2f}%")
    row1_kpis[2].metric("Avg Transaction Value (ATV)", f"${atv:,.2f}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    row2_kpis = st.columns(3)
    row2_kpis[0].metric("Return Rate %", f"{return_rate:.2f}%")
    row2_kpis[1].metric("Discount Rate %", f"{discount_rate:.2f}%")
    row2_kpis[2].metric("Conversion Rate %", f"{conversion_rate:.2f}%")
        
    st.markdown("---")
    
    # Chart Visualizations
    st.subheader("📈 Trend & Regional Analysis")
    row1_col1, row1_col2 = st.columns([2, 1])
    
    with row1_col1:
        weekly_trend = filtered_df.groupby('week_start_date')['net_sales'].sum().reset_index()
        fig_trend = px.line(weekly_trend, x='week_start_date', y='net_sales', title='Weekly Net Sales Trend', markers=True)
        fig_trend.update_layout(height=400, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_trend, width='stretch')
        
    with row1_col2:
        sales_by_region = filtered_df.groupby('region')['net_sales'].sum().reset_index()
        fig_region = px.bar(sales_by_region, x='region', y='net_sales', title='Net Sales by Region', color='net_sales', color_continuous_scale='Blues')
        fig_region.update_layout(height=400, template='plotly_white', showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_region, width='stretch')

    st.subheader("🏷️ Category & Store Intelligence")
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        cat_performance = filtered_df.groupby('product_category')['net_sales'].sum().reset_index().sort_values('net_sales', ascending=True)
        fig_cat = px.bar(cat_performance, x='net_sales', y='product_category', orientation='h', title='Category Performance by Net Sales', color='net_sales', color_continuous_scale='GnBu')
        fig_cat.update_layout(height=400, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_cat, width='stretch')
        
    with row2_col2:
        store_leaderboard = filtered_df.groupby('store_name')['net_sales'].sum().reset_index().sort_values('net_sales', ascending=False).head(10)
        fig_store = px.bar(store_leaderboard, x='store_name', y='net_sales', title='Top Stores by Net Sales', color='net_sales', color_continuous_scale='Viridis')
        fig_store.update_layout(height=400, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_store, width='stretch')

    st.subheader("⚠️ Supply Chain & Operational Risks")
    row3_col1, row3_col2 = st.columns(2)
    
    with row3_col1:
        stockout_risk = filtered_df.groupby('product_category')['stockouts'].sum().reset_index().sort_values('stockouts', ascending=False)
        fig_stockout = px.bar(stockout_risk, x='product_category', y='stockouts', title='Stockout Incidents', color='stockouts', color_continuous_scale='Reds')
        fig_stockout.update_layout(height=350, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_stockout, width='stretch')
        
    with row3_col2:
        return_risk = filtered_df.groupby('product_category')['returns_amount'].sum().reset_index().sort_values('returns_amount', ascending=False)
        fig_returns = px.bar(return_risk, x='product_category', y='returns_amount', title='Total Returns Claim Value', color='returns_amount', color_continuous_scale='YlOrRd')
        fig_returns.update_layout(height=350, template='plotly_white', margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_returns, width='stretch')

    st.markdown("---")
    st.subheader("💡 Dynamic Business Insights")
    insight_cols = st.columns(3)
    
    with insight_cols[0]:
        region_sales = filtered_df.groupby('region')['net_sales'].sum()
        if not region_sales.empty:
            st.markdown(f'<div class="insight-card"><div class="insight-title">Region Performance</div><ul><li><b>Top Region:</b> {region_sales.idxmax()} (${region_sales.max():,.2f})</li><li><b>Low Region:</b> {region_sales.idxmin()} (${region_sales.min():,.2f})</li></ul></div>', unsafe_allow_html=True)

    with insight_cols[1]:
        store_target_df = filtered_df.groupby('store_name')[['net_sales', 'sales_target']].sum().reset_index()
        underperforming = [f"<li>{r['store_name']}: <b>{(r['net_sales']/r['sales_target']*100):.1f}%</b></li>" for _, r in store_target_df.iterrows() if r['sales_target'] > 0 and (r['net_sales']/r['sales_target']) < 1.0]
        if underperforming:
            st.markdown(f'<div class="insight-card-warning"><div class="insight-title">Stores Missing Target</div><ul>{"".join(underperforming[:4])}</ul></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="insight-card"><div class="insight-title">Targets Status</div><p>🎉 All stores reached target goals.</p></div>', unsafe_allow_html=True)

    with insight_cols[2]:
        cat_returns_series = filtered_df.groupby('product_category')['returns_amount'].sum().sort_values(ascending=False)
        if not cat_returns_series.empty and cat_returns_series.sum() > 0:
            ret_list = "".join([f"<li>{cat}: <b>${val:,.2f}</b></li>" for cat, val in cat_returns_series.head(2).items()])
            st.markdown(f'<div class="insight-card-warning"><div class="insight-title">High Return Categories</div><ul>{ret_list}</ul></div>', unsafe_allow_html=True)

    st.markdown("### 📤 Export Filtered Data")
    st.download_button(label="📥 Download Filtered Dataset as CSV File", data=filtered_df.to_csv(index=False).encode('utf-8'), file_name="filtered_sales.csv", mime="text/csv")
    
    with st.expander("🔍 View Raw Filtered Data (Top 50 rows)"):
        st.dataframe(filtered_df.head(50), width='stretch')
else:
    st.info("👋 Upload 'retail_weekly_sales.xlsx' and 'store_master.xlsx' in the sidebar to get started.")
