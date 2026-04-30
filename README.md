# HealthCo Operations Monitoring Dashboard

## Overview
This dashboard analyzes 7 days of operational data (Feb 9-15, 2026) across HealthCo's Integration Engine, Platform API, and AI Agent Runtime to identify anomalies, correlate cross-system issues, and provide actionable recommendations for the on-call team.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Install required libraries:**
```bash
pip install streamlit pandas plotly numpy matplotlib
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

2. **Verify data files are in the same directory as `ops_dashboard.py`:**
   - `ingestion_logs.csv`
   - `agent_call_outcomes.csv`
   - `api_health_metrics.csv`
   - `system_alerts.json`

## Running the Dashboard

**Start the dashboard:**
```bash
streamlit run ops_dashboard.py
```

The dashboard will automatically open in your browser at `http://localhost:8501`

**To stop the dashboard:**
Press `Ctrl+C` in the terminal

## Dashboard Features

### Executive Summary
- Overall system health metrics (ingestion success, call success, open alerts)
- Top 3 urgent issues with specific details and recommended actions
- Color-coded by priority (red/orange/blue)

### Ingestion Health Analysis
- Failure rates by customer (bar chart)
- Validation layer breakdown (pie chart + detailed breakdown for worst customer)
- Highlights problematic customers and validation layers

### Agent Call Outcomes Analysis  
- Call outcome distribution (pie chart)
- Call outcomes over time (stacked area chart)
- Error rates by customer (bar chart)
- Error rates by provider (top 10 worst providers table)
- Call error timeline

### API Health & System Alerts
- API error rate timeline with circuit breaker events highlighted
- Alert summary by severity (resolved vs unresolved)
- Alert summary by type
- Unacknowledged alerts breakdown
- Alert statistics

### Anomaly Detection & Correlation
- **Anomaly 1:** Circuit breaker impact on downstream agent calls (timeline correlation)
- **Anomaly 2:** Customer-specific correlation between ingestion failures and call errors (scatter plot)
- Statistical analysis with before/during comparisons

### Actionable Recommendations
- Immediate actions (next 2 hours) with specific owners and timelines
- Short-term improvements (this week)

## Technical Approach

### Data Processing
- Used pandas for data loading and aggregation
- Converted timestamps to datetime for time-series analysis
- Created derived fields (is_failure, is_error) for cleaner analysis
- Filtered low-volume hours to avoid statistical noise

### Anomaly Detection Methods
1. **Circuit breaker correlation:** Compared agent call error rates before vs during circuit breaker OPEN period
2. **Customer-level correlation:** Analyzed relationship between ingestion failures and agent call errors by customer
3. **Customer comparison:** Identified customers with failure rates significantly above average

### Visualization
- Streamlit for interactive dashboard framework
- Plotly for charts (bar, line, scatter, pie, area)
- Color-coded priority boxes (red/orange/blue for P1/P2/P3)
- Red shading on timeline charts to highlight circuit breaker periods
- Gradient coloring on tables to highlight high error rates

### Key Design Decisions
- Removed misleading percentage-based timelines for low-volume data
- Focused on actionable insights over statistical complexity
- Prioritized visual clarity and ease of interpretation
- Used tables for detailed breakdowns, charts for patterns and trends

## Key Findings

See `FINDINGS.md` for detailed operational findings and recommended actions.

## Author Notes

Built using Python, Streamlit, pandas, and plotly for data analysis and visualization. Used Claude AI assistance as recommended during the interview process. 

**My contribution:** Operational analysis approach, identifying which metrics matter, correlation logic, prioritization of issues, and actionable recommendations based on 10 years of production operations experience.

**Claude's contribution:** Python/Streamlit syntax, code structure, and implementation of the analysis logic I designed.

**Time spent:** Approximately 90 minutes of focused work including data exploration, dashboard development, and documentation.
