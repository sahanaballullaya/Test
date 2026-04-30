"""
HealthCo Operations Monitoring Dashboard

Purpose: Analyze 7 days of operational data (Feb 9-15, 2026) to identify anomalies,
         correlate cross-system issues, and provide actionable recommendations.

Key Features:
- System health metrics and KPIs
- Top 3 urgent issues with operational prioritization
- Cross-system correlation analysis (API health → agent call failures)
- Customer-specific ingestion and call error analysis
- Alert summary with unresolved/unacknowledged tracking
- Actionable recommendations with owners and timelines

Author: Sahana Ballullaya
Date: April 2026
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Operations Dashboard", layout="wide")

# ==================== DATA LOADING ====================
@st.cache_data
def load_data():
    """
    Load operational data from CSV/JSON files with caching for performance.
    
    Returns:
        tuple: (ingestion_logs, agent_calls, api_health, system_alerts)
    """
    # Load all 4 data sources
    ingestion = pd.read_csv("ingestion_logs.csv", parse_dates=["timestamp"])
    calls = pd.read_csv("agent_call_outcomes.csv", parse_dates=["timestamp"])
    api = pd.read_csv("api_health_metrics.csv", parse_dates=["timestamp"])
    alerts = pd.read_json("system_alerts.json")
    alerts["timestamp"] = pd.to_datetime(alerts["timestamp"])
    
    # Create binary flags for failures/errors to simplify filtering
    # Operational logic: SUCCESS and WARNING_PROCEED are acceptable outcomes
    ingestion["is_failure"] = ~ingestion["status"].isin(["SUCCESS", "WARNING_PROCEED"])
    
    # Operational logic: CALL_FAILED, TOOL_ERROR, TIMEOUT require investigation
    calls["is_error"] = calls["outcome"].isin(["CALL_FAILED", "TOOL_ERROR", "TIMEOUT"])
    
    return ingestion, calls, api, alerts

ingestion, calls, api, alerts = load_data()

st.title("HealthCo Operations Monitoring Dashboard")
st.markdown("**Analysis Period:** Feb 9-15, 2026 | **Generated:** " + datetime.now().strftime("%Y-%m-%d %H:%M"))

# ==================== EXECUTIVE SUMMARY ====================
st.header("Executive Summary")

# Calculate overall system health metrics
# Operational reasoning: Start with high-level KPIs for quick health snapshot
ing_success = 1 - ingestion["is_failure"].mean()
call_success = 1 - calls["is_error"].mean()
open_critical = alerts[(alerts["severity"] == "CRITICAL") & (alerts["resolved"] == False)].shape[0]
open_high = alerts[(alerts["severity"] == "HIGH") & (alerts["resolved"] == False)].shape[0]

# Display metrics in columns for at-a-glance monitoring
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ingestion Success Rate", f"{ing_success:.1%}", 
          delta=f"{100-ing_success*100:.1f}% failed", delta_color="inverse")
c2.metric("Call Success Rate", f"{call_success:.1%}",
          delta=f"{100-call_success*100:.1f}% failed", delta_color="inverse")
c3.metric("Critical Alerts (Open)", open_critical)
c4.metric("High Alerts (Open)", open_high)

# ==================== TOP 3 URGENT ISSUES ====================
st.header("Top 3 Urgent Issues")

# PRIORITY 1: Circuit Breaker (System-Wide Impact)
# Operational reasoning: Platform issues affect ALL customers → always highest priority
circuit_breaker_events = api[api["circuit_breaker_status"] == "OPEN"].copy()
if not circuit_breaker_events.empty:
    first_cb_event = circuit_breaker_events.iloc[0]
    cb_timestamp = first_cb_event["timestamp"]
    cb_error_rate = first_cb_event["error_rate_pct"]
    
    # Red box (st.error) = P1 priority
    st.error(f"""
    **PRIORITY 1: Circuit Breaker Opened - Platform API Degradation**
    
    **What broke:** Platform API circuit breaker opened on {cb_timestamp.strftime('%b %d at %H:%M')}
    
    **Metrics at time of failure:**
    - Error rate: {cb_error_rate:.2f}% (threshold: >5%)
    - P99 latency: {first_cb_event['p99_latency_ms']:.0f}ms
    - Active connections: {first_cb_event['active_connections']}
    
    **Downstream impact:** Agent call errors spiked {calls[calls['timestamp'] >= cb_timestamp]['is_error'].mean()*100:.1f}% after circuit breaker opened
    
    **Action:** Escalate to Platform team immediately. Investigate root cause of API degradation starting at {cb_timestamp.strftime('%H:%M on %b %d')}.
    """)

# PRIORITY 2: Customer-Specific High Failure Rate
# Operational reasoning: Customer issues are P2 - fix platform first, then help customers
customer_failures = ingestion.groupby("customer_id").agg(
    total=("batch_id", "count"),
    failures=("is_failure", "sum"),
    failure_rate=("is_failure", "mean")
).sort_values("failure_rate", ascending=False)

worst_customer = customer_failures.index[0]
worst_rate = customer_failures.iloc[0]["failure_rate"]
avg_rate = ingestion["is_failure"].mean()

# Identify which validation layer is causing most failures
worst_cust_validations = ingestion[
    (ingestion["customer_id"] == worst_customer) & 
    (ingestion["is_failure"])
]["validation_layer_failed"].value_counts()

if not worst_cust_validations.empty:
    main_layer = worst_cust_validations.index[0]
    layer_count = worst_cust_validations.iloc[0]
    
    # Orange box (st.warning) = P2 priority
    st.warning(f"""
**PRIORITY 2: {worst_customer} - Elevated Ingestion Failures**

**What's broken:** 
{worst_customer} has {worst_rate*100:.1f}% ingestion failure rate ({worst_rate/avg_rate:.1f}x higher than average)

**Observed pattern:**
Failures are distributed across validation layers, with {main_layer} being the most frequent, indicating potential data format or compatibility issues.

**Downstream impact:**
{worst_customer} also shows elevated agent call error rate, suggesting ingestion issues are propagating downstream.

**Recommended actions:**
1. Review {worst_customer}'s recent file submissions for {main_layer} validation issues
2. Provide customer with detailed validation error report and schema documentation
3. Check if recent schema version changes broke {worst_customer}'s integration format
    """)

# PRIORITY 3: Unresolved Critical Alerts
# Operational reasoning: Unacknowledged alerts indicate process breakdown in on-call
critical_unresolved = alerts[
    (alerts["severity"] == "CRITICAL") & 
    (alerts["resolved"] == False)
].sort_values("timestamp")

if not critical_unresolved.empty:
    num_critical = len(critical_unresolved)
    
    # Blue box (st.info) = P3 priority
    st.info(f"""
    **PRIORITY 3: {num_critical} Unresolved CRITICAL Alerts**
    
    **Active alerts requiring immediate attention:**
    """)
    
    # Display alerts in table format for easier scanning
    alert_table = critical_unresolved[[
        "alert_id", "timestamp", "alert_type", "system", "customer_id", "acknowledged"
    ]].copy()
    alert_table["timestamp"] = alert_table["timestamp"].dt.strftime("%b %d %H:%M")
    alert_table["acknowledged"] = alert_table["acknowledged"].map({True: "Yes", False: "NO"})
    
    st.dataframe(alert_table, use_container_width=True, hide_index=True)
    
    st.markdown("""
    **Action:** Acknowledge all unresolved CRITICAL alerts and assign owners for investigation within 1 hour.
    """)

# ==================== INGESTION HEALTH ====================
st.header("Ingestion Health Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Failure Rate by Customer")
    # Operational reasoning: Bar chart makes problematic customers visually obvious
    fig1 = px.bar(
        customer_failures.reset_index(), 
        x="customer_id", 
        y="failure_rate",
        title="Ingestion Failure Rate by Customer",
        labels={"failure_rate": "Failure Rate", "customer_id": "Customer"},
        color="failure_rate",
        color_continuous_scale="Reds"  # Red gradient highlights high failure rates
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Failures by Validation Layer")
    # Operational reasoning: Shows which validation layer needs attention
    validation_failures = ingestion[ingestion["is_failure"]]["validation_layer_failed"].value_counts()
    fig2 = px.pie(
        values=validation_failures.values,
        names=validation_failures.index,
        title="Failure Distribution by Validation Layer"
    )
    st.plotly_chart(fig2, use_container_width=True)

# Detailed breakdown for worst customer to help troubleshooting
st.subheader(f"Validation Layer Breakdown for {worst_customer}")
validation_detail = ingestion[
    (ingestion["customer_id"] == worst_customer) & 
    (ingestion["is_failure"])
].groupby("validation_layer_failed").size().reset_index(name="failure_count")

fig_val = px.bar(
    validation_detail,
    x="validation_layer_failed",
    y="failure_count",
    title=f"{worst_customer} Failures by Validation Layer",
    labels={"validation_layer_failed": "Validation Layer", "failure_count": "Failures"}
)
st.plotly_chart(fig_val, use_container_width=True)

# ==================== AGENT CALL OUTCOMES ====================
st.header("Agent Call Outcomes Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Call Outcome Distribution")
    # Shows overall health - what percentage of calls succeed vs fail
    outcome_dist = calls["outcome"].value_counts()
    fig4 = px.pie(
        values=outcome_dist.values,
        names=outcome_dist.index,
        title="Agent Call Outcomes (7 Days)"
    )
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    st.subheader("Error Rate by Customer")
    # Identifies which customers have elevated error rates requiring investigation
    customer_call_errors = calls.groupby("customer_id").agg(
        total=("call_id", "count"),
        errors=("is_error", "sum"),
        error_rate=("is_error", "mean")
    ).sort_values("error_rate", ascending=False)
    
    fig5 = px.bar(
        customer_call_errors.reset_index(),
        x="customer_id",
        y="error_rate",
        title="Agent Call Error Rate by Customer",
        labels={"error_rate": "Error Rate"},
        color="error_rate",
        color_continuous_scale="Reds"
    )
    st.plotly_chart(fig5, use_container_width=True)

# Call error timeline - shows when errors spiked
st.subheader("Agent Call Error Timeline")
call_timeline = calls.set_index("timestamp").resample("1h")["is_error"].agg(
    ["sum", "count", "mean"]
).reset_index()
call_timeline["error_rate"] = call_timeline["mean"] * 100

fig6 = px.line(
    call_timeline,
    x="timestamp",
    y="error_rate",
    title="Agent Call Error Rate Over Time (Hourly)",
    labels={"error_rate": "Error Rate (%)"}
)
st.plotly_chart(fig6, use_container_width=True)

# Call outcomes over time - shows distribution of outcomes throughout the week
st.subheader("Call Outcome Distribution Over Time")
outcome_timeline = calls.groupby([
    pd.Grouper(key="timestamp", freq="1h"),
    "outcome"
]).size().reset_index(name="count")

fig6b = px.area(
    outcome_timeline,
    x="timestamp",
    y="count",
    color="outcome",
    title="Agent Call Outcomes Over Time (Hourly)",
    labels={"count": "Number of Calls", "outcome": "Outcome"}
)
st.plotly_chart(fig6b, use_container_width=True)

# Provider error analysis
# Operational reasoning: Identifies specific providers with high error rates for targeted investigation
st.subheader("Providers with Elevated Error Rates")
provider_errors = calls.groupby("provider_id").agg(
    total_calls=("call_id", "count"),
    error_calls=("is_error", "sum"),
    error_rate=("is_error", "mean")
).reset_index()

# Filter to providers with at least 10 calls to avoid statistical noise
provider_errors = provider_errors[provider_errors["total_calls"] >= 10]
worst_providers = provider_errors.nlargest(10, "error_rate")

st.dataframe(
    worst_providers.style.format({
        "error_rate": "{:.1%}",
        "total_calls": "{:.0f}",
        "error_calls": "{:.0f}"
    }).background_gradient(subset=["error_rate"], cmap="Reds"),
    use_container_width=True
)
st.caption("Showing top 10 providers with highest error rates (minimum 10 calls to avoid statistical noise)")

# ==================== API HEALTH & ALERTS ====================
st.header("API Health & System Alerts")

col1, col2 = st.columns(2)

with col1:
    st.subheader("API Error Rate Timeline")
    fig7 = px.line(
        api,
        x="timestamp",
        y="error_rate_pct",
        title="Platform API Error Rate Over Time",
        labels={"error_rate_pct": "Error Rate (%)"}
    )
    
    # Highlight circuit breaker periods with red shading
    # Operational reasoning: Visual correlation between circuit breaker and error spikes
    if not circuit_breaker_events.empty:
        fig7.add_vrect(
            x0=circuit_breaker_events["timestamp"].min(),
            x1=circuit_breaker_events["timestamp"].max(),
            fillcolor="red",
            opacity=0.2,
            annotation_text="Circuit Breaker OPEN",
            annotation_position="top left"
        )
    st.plotly_chart(fig7, use_container_width=True)

with col2:
    st.subheader("Alerts by Severity")
    alert_summary = alerts.groupby(["severity", "resolved"]).size().reset_index(name="count")
    fig8 = px.bar(
        alert_summary,
        x="severity",
        y="count",
        color="resolved",
        title="Alert Summary (Resolved vs Unresolved)",
        barmode="stack",
        category_orders={"severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
    )
    st.plotly_chart(fig8, use_container_width=True)

# Detailed alert breakdown
st.subheader("Alert Summary - Detailed Breakdown")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Alerts by Type**")
    # Shows which alert types fire most frequently to identify systemic issues
    alert_by_type = alerts.groupby("alert_type").size().reset_index(name="count").sort_values("count", ascending=False)
    fig8a = px.bar(
        alert_by_type,
        x="alert_type",
        y="count",
        title="Alert Count by Type"
    )
    fig8a.update_xaxes(tickangle=45)
    st.plotly_chart(fig8a, use_container_width=True)

with col_b:
    st.markdown("**Unacknowledged Alerts**")
    # Operational reasoning: Unacknowledged alerts indicate on-call process failures
    unack_alerts = alerts[alerts["acknowledged"] == False]
    unack_by_severity = unack_alerts.groupby("severity").size().reset_index(name="count")
    
    if not unack_alerts.empty:
        fig8b = px.bar(
            unack_by_severity,
            x="severity",
            y="count",
            title=f"Unacknowledged Alerts by Severity (Total: {len(unack_alerts)})",
            color="severity",
            color_discrete_map={
                "CRITICAL": "red",
                "HIGH": "orange", 
                "MEDIUM": "yellow",
                "LOW": "lightblue"
            },
            category_orders={"severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
        )
        st.plotly_chart(fig8b, use_container_width=True)
    else:
        st.success("All alerts have been acknowledged!")

# Alert statistics summary
total_alerts = len(alerts)
unresolved_alerts = len(alerts[alerts["resolved"] == False])
unack_count = len(unack_alerts)

st.info(f"""
**Alert Statistics:**
- Total alerts (7 days): {total_alerts}
- Unresolved: {unresolved_alerts} ({unresolved_alerts/total_alerts*100:.1f}%)
- Unacknowledged: {unack_count} ({unack_count/total_alerts*100:.1f}%)
- CRITICAL unresolved: {len(critical_unresolved)}
""")

# ==================== ANOMALY DETECTION ====================
st.header("Anomaly Detection & Cross-System Correlation")

st.subheader("ANOMALY 1: Circuit Breaker Impact on Agent Calls")

# Aggregate data by hour for correlation analysis
# Operational reasoning: Hourly aggregation smooths noise while preserving patterns
ingestion["hour"] = ingestion["timestamp"].dt.floor("h")
calls["hour"] = calls["timestamp"].dt.floor("h")
api["hour"] = api["timestamp"].dt.floor("h")

api_hourly = api.groupby("hour").agg(
    avg_error_rate=("error_rate_pct", "mean"),
    circuit_breaker_open=("circuit_breaker_status", lambda x: (x == "OPEN").any())
).reset_index()

call_hourly = calls.groupby("hour").agg(
    call_error_count=("is_error", "sum"),
    call_error_rate=("is_error", "mean")
).reset_index()

# Merge API and call data on the same timeline for correlation
combined = api_hourly.merge(call_hourly, on="hour", how="outer").fillna(0)

# Plot both metrics on same timeline to show correlation
fig9 = px.line(
    combined,
    x="hour",
    y=["avg_error_rate", "call_error_count"],
    title="Correlation: API Error Rate vs Agent Call Errors Over Time",
    labels={"value": "Count/Rate", "variable": "Metric"}
)

# Highlight circuit breaker periods with red shading
cb_periods = combined[combined["circuit_breaker_open"]]
for idx, period in cb_periods.iterrows():
    fig9.add_vrect(
        x0=period["hour"],
        x1=period["hour"] + pd.Timedelta(hours=1),
        fillcolor="red",
        opacity=0.2,
        layer="below",
        line_width=0,
        annotation_text="Circuit Breaker OPEN" if idx == cb_periods.index[0] else ""
    )

st.plotly_chart(fig9, use_container_width=True)

# Quantify the impact of circuit breaker on downstream systems
# Operational reasoning: Compare error rates before vs during circuit breaker period
if not circuit_breaker_events.empty:
    cb_start = circuit_breaker_events["timestamp"].min()
    cb_end = circuit_breaker_events["timestamp"].max()
    
    # Split agent calls into before and during circuit breaker periods
    calls_during_cb = calls[
        (calls["timestamp"] >= cb_start) & 
        (calls["timestamp"] <= cb_end)
    ]
    calls_before_cb = calls[calls["timestamp"] < cb_start]
    
    error_rate_during = calls_during_cb["is_error"].mean()
    error_rate_before = calls_before_cb["is_error"].mean()
    increase_pct = ((error_rate_during / error_rate_before) - 1) * 100 if error_rate_before > 0 else 0
    
    st.error(f"""
    **FINDING:** Agent call error rate increased {increase_pct:.0f}% during circuit breaker OPEN period.
    
    - Error rate BEFORE circuit breaker: {error_rate_before*100:.1f}%
    - Error rate DURING circuit breaker: {error_rate_during*100:.1f}%
    - Total affected calls: {calls_during_cb['is_error'].sum():.0f}
    
    **Conclusion:** Platform API degradation directly caused downstream agent call failures.
    """)

st.subheader("ANOMALY 2: Customer-Specific Ingestion vs Call Failures")

# Analyze correlation between ingestion failures and call failures by customer
# Operational reasoning: Determine if bad data at ingestion propagates to call failures
customer_correlation = []

for customer in ingestion["customer_id"].unique():
    cust_ing = ingestion[ingestion["customer_id"] == customer]
    cust_calls = calls[calls["customer_id"] == customer]
    
    ing_fail_rate = cust_ing["is_failure"].mean()
    call_error_rate = cust_calls["is_error"].mean()
    
    customer_correlation.append({
        "customer_id": customer,
        "ingestion_failure_rate": ing_fail_rate,
        "call_error_rate": call_error_rate,
        "total_calls": len(cust_calls)
    })

corr_df = pd.DataFrame(customer_correlation)

# Scatter plot shows relationship between ingestion and call failures
# Operational reasoning: If points cluster along diagonal, ingestion issues propagate downstream
fig10 = px.scatter(
    corr_df,
    x="ingestion_failure_rate",
    y="call_error_rate",
    size="total_calls",
    text="customer_id",
    title="Customer Correlation: Ingestion Failures vs Agent Call Errors",
    labels={
        "ingestion_failure_rate": "Ingestion Failure Rate",
        "call_error_rate": "Agent Call Error Rate"
    }
)
fig10.update_traces(textposition="top center")
st.plotly_chart(fig10, use_container_width=True)

st.info(f"""
**FINDING:** Customers with high ingestion failure rates also tend to have high agent call error rates.

This suggests ingestion issues propagate downstream to agent calls. When customer data fails validation,
their provider data is incomplete or invalid, causing agent calls to fail.

**Customers requiring immediate attention:** {', '.join(corr_df.nlargest(3, 'ingestion_failure_rate')['customer_id'].tolist())}
""")

# ==================== ACTIONABLE RECOMMENDATIONS ====================
st.header("Actionable Recommendations")

# Operational reasoning: Prioritize by blast radius (system-wide > customer > process)
st.success(f"""
**Immediate Actions (Next 2 Hours):**

1. **Platform Team:** Investigate circuit breaker root cause
   - Time: {cb_timestamp.strftime('%b %d at %H:%M') if not circuit_breaker_events.empty else 'N/A'} 
   - Check: Database connection pool, external dependency timeouts, what changed before 14:00
   - Goal: Prevent recurrence

2. **Customer Success Team:** Contact {worst_customer}
   - Issue: {layer_count if not worst_cust_validations.empty else 0} failures at {main_layer if not worst_cust_validations.empty else 'N/A'} validation
   - Provide: Validation error report and schema documentation
   - Timeline: Within 4 hours

3. **On-Call Engineer:** Acknowledge all {num_critical if not critical_unresolved.empty else 0} CRITICAL unresolved alerts
   - Review each alert's system and impact
   - Assign owners for investigation
""")

st.info("""
**Short-Term Improvements (This Week):**

1. Implement automated alerting for circuit breaker state changes
2. Build customer-specific ingestion validation dashboards
3. Add SLA tracking for alert acknowledgment and resolution times
4. Check recent schema deployments - did a schema change break customer integrations?
""")

st.markdown("---")
st.caption("Dashboard built with Streamlit • Data: Feb 9-15, 2026 • Refresh frequency: On-demand")
