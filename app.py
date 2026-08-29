"""
Bird Species Observation Analysis — Streamlit Dashboard
Forest vs Grassland bird monitoring data (11 NPS admin units, 2018 survey season)

Run with:  streamlit run app.py
Requires:  bird_observations_cleaned.csv and admin_units_lookup.csv in the same folder
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bird Species Observation Analysis ",
    page_icon="🐦",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Data loading (cached so it only runs once per session)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    obs = pd.read_csv("bird_observations_cleaned.csv", parse_dates=["Date"])
    admin = pd.read_csv("admin_units_lookup.csv")
    obs = obs.merge(admin, on="Admin_Unit_Code", how="left")
    return obs, admin


df, admin_units = load_data()

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.title("🐦 Filters")

habitat_options = sorted(df["Habitat_Type"].dropna().unique())
season_options = sorted(df["Season"].dropna().unique())
park_options = sorted(df["Park_Name"].dropna().unique())

sel_habitat = st.sidebar.multiselect("Habitat Type", habitat_options, default=habitat_options)
sel_season = st.sidebar.multiselect("Season", season_options, default=season_options)
sel_park = st.sidebar.multiselect("Park / Admin Unit", park_options, default=park_options)
watchlist_only = st.sidebar.checkbox("Show only PIF Watchlist species", value=False)

filtered = df[
    df["Habitat_Type"].isin(sel_habitat)
    & df["Season"].isin(sel_season)
    & df["Park_Name"].isin(sel_park)
]
if watchlist_only:
    filtered = filtered[filtered["PIF_Watchlist_Status"] == True]  # noqa: E712

st.sidebar.markdown("---")
st.sidebar.caption(f"{len(filtered):,} of {len(df):,} observations shown")

# ----------------------------------------------------------------------------
# Header + KPI row
# ----------------------------------------------------------------------------
st.title("Bird Species Observation Analysis — by Shreya Mohite")
st.caption("Forest vs. Grassland bird monitoring across 11 National Park Service units — 2018 survey season")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Observations", f"{len(filtered):,}")
k2.metric("Unique Species", f"{filtered['Scientific_Name'].nunique():,}")
k3.metric("Watchlist Species", f"{filtered.loc[filtered['PIF_Watchlist_Status'] == True, 'Scientific_Name'].nunique():,}")  # noqa: E712
k4.metric("Sites Surveyed", f"{filtered['Site_Name'].nunique():,}")

st.markdown("---")

# ----------------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------------
tab_overview, tab_map, tab_species, tab_env, tab_data = st.tabs(
    ["📊 Overview", "🗺️ Site Map", "🐤 Species Insights", "🌤️ Environment", "📋 Data"]
)

# --- Overview -----------------------------------------------------------
with tab_overview:
    c1, c2 = st.columns(2)

    with c1:
        habitat_counts = filtered["Habitat_Type"].value_counts().reset_index()
        habitat_counts.columns = ["Habitat_Type", "Observations"]
        fig = px.bar(
            habitat_counts, x="Habitat_Type", y="Observations", color="Habitat_Type",
            title="Observations by Habitat",
            color_discrete_map={"Forest": "#2E7D32", "Grassland": "#C9A227"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        season_counts = filtered["Season"].value_counts().reset_index()
        season_counts.columns = ["Season", "Observations"]
        fig = px.bar(
            season_counts, x="Season", y="Observations", color="Season",
            title="Observations by Season",
        )
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        method_counts = filtered["ID_Method"].value_counts().reset_index()
        method_counts.columns = ["ID_Method", "Observations"]
        fig = px.pie(
            method_counts, names="ID_Method", values="Observations",
            title="Identification Method Breakdown", hole=0.45,
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        monthly = filtered.groupby(["Month_Name", "Month"]).size().reset_index(name="Observations")
        monthly = monthly.sort_values("Month")
        fig = px.line(
            monthly, x="Month_Name", y="Observations", markers=True,
            title="Observations by Month",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.info(
        "Forest and Grassland show nearly identical species richness in this dataset "
        "(108 vs 107 species overall) — habitat type alone doesn't predict diversity here."
    )

# --- Site Map -------------------------------------------------------------
with tab_map:
    site_summary = (
        filtered.groupby(["Park_Name", "Latitude", "Longitude"])
        .agg(
            Total_Observations=("Scientific_Name", "count"),
            Unique_Species=("Scientific_Name", "nunique"),
            Watchlist_Species=("PIF_Watchlist_Status", "sum"),
        )
        .reset_index()
    )

    fig = px.scatter_map(
        site_summary,
        lat="Latitude", lon="Longitude",
        size="Total_Observations", color="Unique_Species",
        hover_name="Park_Name",
        hover_data={"Total_Observations": True, "Unique_Species": True, "Watchlist_Species": True,
                    "Latitude": False, "Longitude": False},
        zoom=7, height=550,
        color_continuous_scale="Greens",
        title="Observation Activity by Park",
    )
    fig.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Bubble size reflects total observations (survey effort), not necessarily pure biodiversity — "
        "ANTI has far more survey records than WOTR, for example."
    )

    st.dataframe(
        site_summary.sort_values("Total_Observations", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )

# --- Species Insights -------------------------------------------------------------
with tab_species:
    c1, c2 = st.columns(2)

    with c1:
        top_species = (
            filtered["Common_Name"].value_counts().head(10).reset_index()
        )
        top_species.columns = ["Common_Name", "Observations"]
        fig = px.bar(
            top_species.sort_values("Observations"),
            x="Observations", y="Common_Name", orientation="h",
            title="Top 10 Species Observed",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        sex_habitat = filtered.groupby(["Habitat_Type", "Sex"]).size().reset_index(name="Observations")
        fig = px.bar(
            sex_habitat, x="Habitat_Type", y="Observations", color="Sex",
            title="Sex Distribution by Habitat", barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        dist_counts = filtered["Distance"].value_counts().reset_index()
        dist_counts.columns = ["Distance", "Observations"]
        fig = px.bar(dist_counts, x="Distance", y="Observations", title="Observation Distance Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        watchlist_df = (
            filtered[filtered["PIF_Watchlist_Status"] == True]  # noqa: E712
            .groupby(["Common_Name", "Habitat_Type"])
            .size()
            .reset_index(name="Observations")
            .sort_values("Observations", ascending=False)
        )
        fig = px.bar(
            watchlist_df, x="Common_Name", y="Observations", color="Habitat_Type",
            title="Watchlist Species Sightings",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Watchlist Species Detail")
    st.dataframe(watchlist_df.reset_index(drop=True), use_container_width=True)

# --- Environment -------------------------------------------------------------
with tab_env:
    c1, c2 = st.columns(2)

    with c1:
        temp_bucket = filtered.copy()
        temp_bucket["Temp_Bucket"] = (temp_bucket["Temperature"] // 2 * 2).astype(int)
        temp_agg = (
            temp_bucket.groupby(["Temp_Bucket", "Habitat_Type"])
            .size()
            .reset_index(name="Observations")
        )
        fig = px.line(
            temp_agg, x="Temp_Bucket", y="Observations", color="Habitat_Type",
            markers=True, title="Temperature vs Observation Activity",
            labels={"Temp_Bucket": "Temperature (°C, 2° buckets)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        disturbance_counts = filtered["Disturbance"].value_counts().reset_index()
        disturbance_counts.columns = ["Disturbance", "Observations"]
        fig = px.bar(disturbance_counts, x="Disturbance", y="Observations", title="Disturbance Impact on Sightings")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        sky_counts = filtered["Sky"].value_counts().reset_index()
        sky_counts.columns = ["Sky", "Observations"]
        fig = px.bar(sky_counts, x="Sky", y="Observations", title="Sky Condition vs Observations")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        flyover_by_habitat = (
            filtered.groupby("Habitat_Type")["Flyover_Observed"].mean().reset_index()
        )
        flyover_by_habitat["Flyover %"] = (flyover_by_habitat["Flyover_Observed"] * 100).round(1)
        fig = px.bar(
            flyover_by_habitat, x="Habitat_Type", y="Flyover %", color="Habitat_Type",
            title="Flyover Rate by Habitat (%)",
            color_discrete_map={"Forest": "#2E7D32", "Grassland": "#C9A227"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    avg_temp = filtered["Temperature"].mean()
    avg_dur = filtered["Observation_Duration_Min"].mean()
    m1, m2 = st.columns(2)
    m1.metric("Avg Temperature", f"{avg_temp:.1f} °C")
    m2.metric("Avg Observation Duration", f"{avg_dur:.1f} min")

# --- Raw data browser -------------------------------------------------------------
with tab_data:
    st.subheader("Filtered Observation Records")
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True, height=500)
    st.download_button(
        "Download filtered data as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="bird_observations_filtered.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("Data source: NPS bird monitoring — Forest & Grassland surveys, 2018 season, 11 admin units.")
