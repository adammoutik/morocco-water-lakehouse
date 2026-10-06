import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.storage.minio_handler import get_parquet_from_minio, list_objects_in_prefix

# 1. Page Configuration
st.set_page_config(page_title="Morocco Water Lakehouse", page_icon="🇲🇦", layout="wide")
st.title("🇲🇦 Morocco Water Reliability Lakehouse")
st.markdown("Analyzing the correlation between Tensift basin rainfall and reservoir levels.")

# 2. Data Loading with Streamlit Caching
@st.cache_data
def load_gold_data():
    bucket = "morocco-water-gold"
    files = list_objects_in_prefix(bucket, "analytical/")
    if not files:
        return pd.DataFrame()
    
    latest_file = sorted(files)[-1] # Ensure we grab the most recent execution
    return get_parquet_from_minio(bucket, latest_file)

df = load_gold_data()

if df.empty:
    st.error("No Gold data found in MinIO. Please run the Gold pipeline first.")
else:
    df = df.sort_values('date').reset_index(drop=True)
    # 3. Dynamic Sidebar Filters
    # Automatically find all columns related to dam fill percentages
    dam_cols = [col for col in df.columns if col.endswith('_fill_pct')]
    
    # Format "yacoub_el_mansour_fill_pct" -> "Yacoub El Mansour"
    dam_names = [col.replace('_fill_pct', '').replace('_', ' ').title() for col in dam_cols]
    dam_mapping = dict(zip(dam_names, dam_cols))

    st.sidebar.header("Filter Options")
    selected_dam_name = st.sidebar.selectbox("Select a Reservoir", dam_names)
    selected_dam_col = dam_mapping[selected_dam_name]

    # 4. Top-Level Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric(f"{selected_dam_name} Avg Capacity", f"{df[selected_dam_col].mean():.1f}%")
    col2.metric("Max Regional Temperature", f"{df['max_temp_c'].max()} °C")
    col3.metric("Total Monthly Precipitation", f"{df['precip_mm'].sum()} mm")

    st.divider()

    # 5. Dual-Axis Plotly Chart
    fig = go.Figure()

    # Add Precipitation (Bar Chart)
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['precip_mm'],
        name="Precipitation (mm)",
        yaxis="y1",
        marker_color="rgba(52, 152, 219, 0.6)", # Light blue
    ))

    # Add Dam Fill Percentage (Line Chart)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df[selected_dam_col],
        name=f"{selected_dam_name} Fill %",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color="#2c3e50", width=3) # Dark navy
    ))

    # Configure the Dual Axis layout
    # Configure the Dual Axis layout
    # Configure the Dual Axis layout
    fig.update_layout(
        title=f"Rainfall Impact on {selected_dam_name} Capacity",
        xaxis=dict(title="Date"),
        yaxis=dict(
            title="Precipitation (mm)",
            title_font=dict(color="#2980b9"),
            tickfont=dict(color="#2980b9"),
            showgrid=False
        ),
        yaxis2=dict(
            title="Fill Percentage (%)",
            title_font=dict(color="#2c3e50"),
            tickfont=dict(color="#2c3e50"),
            overlaying="y",
            side="right",
            range=[0, 100] # <--- Locks the capacity scale so 100% is top and 0% is bottom
        ),
        hovermode="x unified",
        height=500
    )

    # Render chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)