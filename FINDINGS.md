# Operational Findings \& Recommendations

**Analysis Period:** Feb 9-15, 2026  
**Prepared for:** On-Call Engineering Lead  
**Dashboard:** See `ops\_dashboard.py` for detailed visualizations

\---

## Executive Summary

Analysis of HealthCo's operational data over 7 days reveals three critical issues requiring immediate attention:

1. **Platform API degradation** causing 90% increase in downstream agent call failures
2. **Customer CUS-105 severe ingestion failures** (40% failure rate, 2.3x higher than average)
3. **10 unresolved CRITICAL alerts** including circuit breaker events and scheduling failure clusters

\---

## Top 3 Operational Issues

### ISSUE 1: Platform API Circuit Breaker Opened - System-Wide Impact

**What happened:**

* Platform API circuit breaker opened on **Feb 13 at 14:00** (2:00 PM)
* Circuit breaker remained OPEN for **4 hours 55 minutes** (until 18:55)
* 53 consecutive 5-minute intervals with circuit breaker OPEN status
* Error rate threshold breached (>5%)

**Impact:**

* **Agent call error rate increased 90.9%** during circuit breaker period

  * Error rate BEFORE circuit breaker: 14.49%
  * Error rate DURING circuit breaker: 27.66%
* Affected all customers system-wide (not customer-specific)
* Elevated latency and timeout rates on agent calls

**How I found it:**

```python
# Method: Filter and compare error rates
# 1. Filtered api\_health\_metrics for circuit\_breaker\_status = "OPEN"
# 2. Found circuit breaker opened Feb 13 at 14:00, closed at 18:55
# 3. Split agent calls into "before" and "during" circuit breaker period
# 4. Calculated error rate for each period
# 5. Found 90.9% increase during circuit breaker period
```

**Root cause hypothesis:**
Platform API reached error rate threshold (>5%) triggering circuit breaker protection. This prevented cascading failures but degraded service for all downstream consumers including Agent Runtime.

**Recommended action:**

1. **IMMEDIATE (Next 1 hour):** Platform team to investigate API logs from Feb 13, 14:00-18:55

   * Check: Database connection pool exhaustion, external dependency timeouts, resource constraints
   * Review: What changed before 14:00? Deployment? Traffic spike? External service degradation?
2. **SHORT-TERM (This week):**

   * Implement automated alerting for circuit breaker state changes with PagerDuty integration
   * Review circuit breaker threshold (is 5% appropriate or should it be higher?)
   * Add circuit breaker half-open state monitoring to prevent repeated failures
3. **LONG-TERM:**

   * Build circuit breaker dashboard showing open/close transitions and correlation with downstream errors
   * Implement retry logic with exponential backoff in Agent Runtime to handle API degradation gracefully

**Priority:** CRITICAL - System-wide outage root cause

\---

### ISSUE 2: Customer CUS-105 - Severe Ingestion Failures

**What happened:**

* CUS-105 has **39.8% ingestion failure rate** (37 failures out of 93 batches)
* Average failure rate across all customers: 17.2%
* **CUS-105 is 2.3x worse than average**

**Failure breakdown by validation layer:**

* SCHEMA validation: 7 failures (19%)
* API\_CONTRACT: 6 failures (16%)
* AI\_SEMANTIC: 6 failures (16%)
* BUSINESS\_RULE: 5 failures (14%)
* Other layers: 13 failures (35%)

**Downstream impact:**
CUS-105 also shows elevated agent call error rates, suggesting ingestion failures propagate downstream:

* When CUS-105 ingestion fails, their provider data is incomplete/invalid → agent calls fail due to missing or incorrect scheduling data

**How I found it:**

```python
# Method: Customer-level aggregation and comparison
# 1. Grouped ingestion data by customer\_id
# 2. Calculated failure rate for each customer
# 3. Identified CUS-105 with 39.8% failure rate vs 17.2% average
# 4. Filtered CUS-105's failed ingestions to count by validation\_layer\_failed
# 5. Found SCHEMA (7), API\_CONTRACT (6), AI\_SEMANTIC (6) as top failure layers
```

**Root cause hypothesis:**
CUS-105's file format does not match expected schema across multiple validation layers. This suggests either:

* Schema version mismatch between customer and HealthCo
* Review CUS-105’s file format for validation issues.
* Check for recent changes on HealthCo side (schema version, API contract, or business rule validation).
* Validate whether backward compatibility was impacted by recent deployments.

**Recommended action:**

1. **IMMEDIATE (Next 2 hours):** Customer Success team to contact CUS-105

   * Provide: Validation error report showing exact failures (field names, expected vs actual)
   * Request: Sample file from customer's current data source
   * Ask: Has anything changed in their provider data export process?
2. **SHORT-TERM (This week):**

   * Run CUS-105's latest file through validation layer and generate detailed error report
   * Provide customer with schema documentation and example valid file
   * **Check recent deployments:** Did we change the schema version recently? If yes, that likely broke CUS-105's integration
   * If schema changed: Either rollback the schema change OR give CUS-105 a migration timeline with support
3. **LONG-TERM:**

   * Implement customer-specific validation dashboards showing failure trends
   * Build automated validation error reports emailed to customers daily
   * Add schema version negotiation (support multiple versions, deprecate old ones gracefully)

**Priority:** HIGH - Customer-specific but high volume impact

\---

### ISSUE 3: 10 Unresolved CRITICAL Alerts - Attention Required

**What happened:**
10 CRITICAL severity alerts remain unresolved across the 7-day period:

* 3x CIRCUIT\_BREAKER\_OPEN (ALT-0026, ALT-0012, ALT-0035)
* 6x SCHEDULING\_FAILURE\_CLUSTER (multiple customers)
* 1x AI\_BLOCKER\_FINDING (CUS-103)

**Breakdown:**

|Alert ID|Timestamp|Type|Customer|Acknowledged|
|-|-|-|-|-|
|ALT-0026|Feb 9 09:19|CIRCUIT\_BREAKER\_OPEN|N/A|Yes|
|ALT-0039|Feb 9 22:10|SCHEDULING\_FAILURE\_CLUSTER|CUS-102|Yes|
|ALT-0055|Feb 10 00:45|AI\_BLOCKER\_FINDING|CUS-103|Yes|
|ALT-0075|Feb 11 00:08|SCHEDULING\_FAILURE\_CLUSTER|CUS-104|NO|
|ALT-0097|Feb 11 06:06|SCHEDULING\_FAILURE\_CLUSTER|N/A|NO|
|ALT-0014|Feb 12 07:33|SCHEDULING\_FAILURE\_CLUSTER|CUS-103|Yes|
|ALT-0060|Feb 12 10:10|SCHEDULING\_FAILURE\_CLUSTER|CUS-101|Yes|
|ALT-0012|Feb 15 08:43|CIRCUIT\_BREAKER\_OPEN|CUS-102|Yes|
|ALT-0035|Feb 15 17:58|CIRCUIT\_BREAKER\_OPEN|N/A|Yes|
|ALT-0029|Feb 15 18:31|SCHEDULING\_FAILURE\_CLUSTER|CUS-102|Yes|

**Concerns:**

* **2 alerts NOT ACKNOWLEDGED** (ALT-0075, ALT-0097) - no one is actively working on these
* **Multiple circuit breaker events** across different days - recurring problem
* **CUS-102 has 3 CRITICAL alerts** - needs dedicated investigation

**How I found it:**

```python
# Method: Alert filtering and grouping
# 1. Filtered alerts where severity = "CRITICAL" AND resolved = False
# 2. Found 10 unresolved critical alerts
# 3. Checked acknowledged status - found 2 unacknowledged (ALT-0075, ALT-0097)
# 4. Grouped alerts by customer\_id - found CUS-102 appears in 3 critical alerts
```

**Recommended action:**

1. **IMMEDIATE (Next 30 minutes):**

   * Acknowledge ALT-0075 and ALT-0097 (currently unacknowledged)
   * Assign owners for each of the 10 alerts
   * Create incident tickets in Jira/ServiceNow for tracking
2. **TODAY:**

   * Investigate why circuit breaker opened 3 separate times (Feb 9, Feb 15 x2)
   * Deep dive CUS-102 (3 CRITICAL alerts) - what's different about this customer?
   * Resolve or escalate each of the 10 alerts with clear next steps
3. **THIS WEEK:**

   * Implement SLA for CRITICAL alert acknowledgment (target: <15 minutes)
   * Add alert auto-escalation if unacknowledged after 30 minutes
   * Build alert fatigue analysis - are we alerting on the right things?

**Priority:** HIGH - Process issue indicating alerting/on-call gaps

\---

## Additional Observations

### Cross-Customer Patterns

* All 5 customers show some ingestion failures, but CUS-105 and CUS-103 are outliers
* SCHEMA validation is the most common failure point (across all customers)
* Feb 13 afternoon (circuit breaker period) shows elevated failures across all systems

### Time-Based Patterns

* Higher failure rates during circuit breaker window (Feb 13, 14:00-19:00)
* Agent call error clusters align with API degradation periods
* No significant day-of-week pattern (failures distributed across all 7 days)

### System Health Baseline

* Normal ingestion success rate: \~83% (when excluding CUS-105)
* Normal agent call success rate: \~85%
* API error rate typically <3% (except during circuit breaker periods)

\---

## Monday Morning Briefing Script

*Here's how I'd present this to the engineering lead:*

**"Good morning. I analyzed the past week's operational data and found three critical issues:**

**First: Platform API had a 5-hour degradation window on Thursday afternoon that caused a 90% spike in agent call failures system-wide. The circuit breaker opened at 2 PM and stayed open until 7 PM. We need the Platform team to investigate what triggered this - my guess is database connection pool exhaustion or an external dependency timeout.**

**Second: Customer CUS-105 has a 40% ingestion failure rate - more than double the average. They're failing across all validation layers, which suggests a file format issue on their end. Customer Success needs to contact them today with a detailed error report and schema guidance.**

**Third: We have 10 unresolved CRITICAL alerts including 3 circuit breaker events and multiple scheduling failure clusters. Two of these aren't even acknowledged yet. We need to assign owners and clear these today.**

**My recommendation: Tackle the API stability issue first since it affects all customers, then work with CUS-105 on their data format, and finally establish better alert triage processes so we don't let CRITICAL alerts sit unresolved.**

**Questions?"**

\---

## How to Extend This Analysis

**For production use, I would add:**

1. **Real-time monitoring:** Convert this dashboard to refresh every 5 minutes with live data
2. **Alerting logic:** Implement automated alerts when:

   * Circuit breaker opens
   * Customer failure rate >30%
   * Agent call error rate >20%
   * CRITICAL alert unacknowledged >30 minutes
3. **Trend analysis:** Compare week-over-week metrics to detect degradation
4. **Customer SLA tracking:** Track whether we're meeting customer SLAs for uptime/latency
5. **Incident correlation:** Link alerts to incident tickets for full lifecycle tracking

\---

**Dashboard Code:** `ops\_dashboard.py`  
**Setup Instructions:** `README.md`  
**Questions:** Contact Sahana Ballullaya

