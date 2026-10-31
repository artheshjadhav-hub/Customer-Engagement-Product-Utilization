
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Customer Engagement Analytics",
    page_icon="🏦",
    layout="wide"
)

st.title("🏦 Customer Engagement & Product Utilization Analytics")
st.caption("Banking Customer Retention Strategy Dashboard")

uploaded = st.file_uploader(
    "Upload Customer CSV",
    type=["csv"]
)

if uploaded is not None:

    df = pd.read_csv(uploaded)

    required = [
        "CustomerId", "Balance", "NumOfProducts",
        "HasCrCard", "IsActiveMember", "Exited",
        "EstimatedSalary", "Geography", "Age"
    ]

    if not set(required).issubset(df.columns):
        st.error("Required dataset columns are missing.")
        st.stop()

    df = df.drop_duplicates().copy()

    if "Surname" in df.columns:
        df = df.drop(columns=["Surname"])

    numeric = [
        "Balance", "NumOfProducts", "HasCrCard",
        "IsActiveMember", "Exited", "EstimatedSalary",
        "Age"
    ]

    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)

    if not df["Exited"].isin([0, 1]).all():
        st.error("Exited must contain only 0 and 1.")
        st.stop()

    if not df["IsActiveMember"].isin([0, 1]).all():
        st.error("IsActiveMember must contain only 0 and 1.")
        st.stop()

    if not df["HasCrCard"].isin([0, 1]).all():
        st.error("HasCrCard must contain only 0 and 1.")
        st.stop()

    if (df["Balance"] < 0).any() or (df["NumOfProducts"] < 1).any():
        st.error("Invalid balance or product count.")
        st.stop()

    df["EngagementProfile"] = np.select(
        [
            (df["IsActiveMember"] == 1) & (df["NumOfProducts"] >= 2),
            (df["IsActiveMember"] == 1) & (df["NumOfProducts"] == 1),
            (df["IsActiveMember"] == 0) & (df["NumOfProducts"] >= 2),
            (df["IsActiveMember"] == 0) & (df["NumOfProducts"] == 1)
        ],
        [
            "Active Engaged",
            "Active Low Product",
            "Inactive Multi Product",
            "Inactive Low Product"
        ],
        default="Other"
    )

    positive = df.loc[df["Balance"] > 0, "Balance"]

    if len(positive):
        threshold = positive.quantile(0.75)
        df["HighValue"] = (
            (df["Balance"] >= threshold) &
            (df["Balance"] > 0)
        )
    else:
        df["HighValue"] = False

    df["AtRiskPremium"] = (
        df["HighValue"] &
        (df["IsActiveMember"] == 0)
    )

    df["RelationshipStrengthIndex"] = (
        df["IsActiveMember"] * 40 +
        (df["NumOfProducts"] >= 2).astype(int) * 40 +
        df["HasCrCard"] * 20
    )

    df["RelationshipTier"] = pd.cut(
        df["RelationshipStrengthIndex"],
        bins=[-1, 39, 79, 100],
        labels=[
            "Weak Relationship",
            "Moderate Relationship",
            "Strong Relationship"
        ]
    )

    st.sidebar.header("Customer Filters")

    geography = st.sidebar.multiselect(
        "Geography",
        df["Geography"].dropna().unique(),
        default=list(df["Geography"].dropna().unique())
    )

    activity = st.sidebar.multiselect(
        "Activity",
        [0, 1],
        default=[0, 1],
        format_func=lambda x: "Active" if x == 1 else "Inactive"
    )

    products = st.sidebar.slider(
        "Number of Products",
        int(df["NumOfProducts"].min()),
        int(df["NumOfProducts"].max()),
        (
            int(df["NumOfProducts"].min()),
            int(df["NumOfProducts"].max())
        )
    )

    balance_limit = st.sidebar.number_input(
        "Minimum Balance",
        min_value=0.0,
        value=0.0
    )

    filtered = df[
        (df["Geography"].isin(geography)) &
        (df["IsActiveMember"].isin(activity)) &
        (df["NumOfProducts"].between(products[0], products[1])) &
        (df["Balance"] >= balance_limit)
    ].copy()

    if filtered.empty:
        st.warning("No customers match these filters.")
        st.stop()

    total = len(filtered)
    churn = int(filtered["Exited"].sum())
    churn_rate = filtered["Exited"].mean() * 100
    active = int((filtered["IsActiveMember"] == 1).sum())
    premium_risk = int(filtered["AtRiskPremium"].sum())

    st.subheader("📊 Customer Engagement Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Customers", f"{total:,}")
    c2.metric("Churned Customers", f"{churn:,}")
    c3.metric("Churn Rate", f"{churn_rate:.2f}%")
    c4.metric("Active Customers", f"{active:,}")

    st.divider()

    st.subheader("1. Engagement vs Churn")

    engagement = filtered.groupby(
        "EngagementProfile"
    )["Exited"].mean().mul(100).reset_index()

    fig = px.bar(
        engagement,
        x="EngagementProfile",
        y="Exited",
        color="EngagementProfile",
        title="Churn Rate by Engagement Profile",
        labels={"Exited": "Churn Rate (%)"}
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("2. Product Utilization Analysis")

    product = filtered.groupby(
        "NumOfProducts"
    )["Exited"].mean().mul(100).reset_index()

    fig2 = px.bar(
        product,
        x="NumOfProducts",
        y="Exited",
        title="Product Count vs Churn",
        labels={"Exited": "Churn Rate (%)"}
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("3. High-value Disengaged Customers")

    st.metric(
        "High-value Disengaged Customers",
        premium_risk
    )

    risk = filtered[filtered["AtRiskPremium"]]

    st.dataframe(
        risk[
            [
                "CustomerId", "Balance",
                "EstimatedSalary", "NumOfProducts",
                "IsActiveMember", "Exited"
            ]
        ],
        use_container_width=True
    )

    st.subheader("4. Relationship Strength Analysis")

    relationship = filtered.groupby(
        "RelationshipTier",
        observed=False
    )["Exited"].mean().mul(100).reset_index()

    fig3 = px.bar(
        relationship,
        x="RelationshipTier",
        y="Exited",
        color="RelationshipTier",
        title="Relationship Strength vs Churn",
        labels={"Exited": "Churn Rate (%)"}
    )

    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("5. Credit Card Stickiness")

    card = filtered.groupby(
        "HasCrCard"
    )["Exited"].mean().mul(100).reset_index()

    card["Card Status"] = card["HasCrCard"].map(
        {0: "No Credit Card", 1: "Credit Card"}
    )

    fig4 = px.bar(
        card,
        x="Card Status",
        y="Exited",
        title="Credit Card Ownership vs Churn",
        labels={"Exited": "Churn Rate (%)"}
    )

    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("6. Customer Data")

    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "Download Filtered Customer Data",
        filtered.to_csv(index=False).encode("utf-8"),
        "filtered_customer_data.csv",
        "text/csv"
    )

else:
    st.info("Please upload your banking customer CSV dataset.")
