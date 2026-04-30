# HealthCo Operations Dashboard

Operations monitoring dashboard analyzing 7 days of system health data (Feb 9-15, 2026).

## Setup

**Requirements:** Python 3.8+

**Installation:**
```bash
pip install streamlit pandas plotly numpy matplotlib
```

**Run:**
```bash
streamlit run dashboard.py
```

Dashboard opens at http://localhost:8501

**Data files required (same directory as dashboard.py):**
- ingestion_logs.csv
- agent_call_outcomes.csv
- api_health_metrics.csv
- system_alerts.json

## What It Shows

**Executive Summary:** System health KPIs, top 3 urgent issues with priority coding (red/orange/blue)

**Ingestion Health:** Failure rates by customer, validation layer breakdown, detailed analysis for worst customer

**Agent Call Outcomes:** Outcome distribution over time, error rates by customer and provider, call timeline

**API Health & Alerts:** Error rate timeline with circuit breaker events, alerts by severity and type, unacknowledged alert tracking

**Anomaly Detection:** Circuit breaker impact on agent calls (correlation timeline), customer-level ingestion vs call failure correlation

**Recommendations:** Immediate actions with owners and timelines

## Key Findings

1. Platform API circuit breaker opened Feb 13 at 14:00, causing 90% increase in agent call errors (14.5% → 27.7%)
2. Customer CUS-105 has 39.8% ingestion failure rate (2.3x above average) at SCHEMA validation layer
3. 10 unresolved CRITICAL alerts including 2 unacknowledged

See FINDINGS.md for detailed analysis.

## Technical Details

**Data processing:** pandas for aggregation, hourly resampling for time-series analysis

**Anomaly detection:** Before/during comparison for circuit breaker impact, customer-level correlation between ingestion and call failures

**Visualization:** Plotly for interactive charts, color gradients on tables for error rate highlighting, red shading on timelines for circuit breaker periods

**Code structure:** Operational reasoning documented in comments throughout dashboard.py

## Author

Sahana Ballullaya  
Built using Python, Streamlit, pandas, Plotly  
Claude AI used for code implementation as recommended by recruiter
