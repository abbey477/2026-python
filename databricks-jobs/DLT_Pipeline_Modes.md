# Databricks DLT: Triggered vs. Continuous Pipeline Modes

---

## What is Pipeline Mode?

Pipeline mode controls **when and how often** your DLT pipeline runs and processes data. There are two options: **Triggered** and **Continuous**.

---

## ⏱ Triggered Mode

The pipeline runs **once**, processes all available data, and then the cluster **shuts down automatically**.

**How it works:**
Trigger (manual / schedule) → Cluster Spins Up → Processes All Data → Cluster Shuts Down

**Key characteristics:**
- Cluster only lives for the duration of the pipeline run — no idle compute spend
- Can be run via a Databricks Job on a cron schedule (hourly, daily, etc.) or triggered manually
- Each table is refreshed based on data available at the time the update starts
- New data won't be processed until the pipeline is triggered again

**Ideal for:** Daily ETL loads · Scheduled batch jobs · On-demand data refreshes · Cost-sensitive workloads

---

## ♾ Continuous Mode

The cluster stays **alive 24/7**, constantly monitoring and processing new data as it arrives.

**How it works:**
Pipeline Starts → Monitors Sources → New Data Arrives → Processes Instantly → Repeats 24/7

**Key characteristics:**
- Processes new data as it arrives — minimal latency between source and destination tables
- Automatically monitors dependent Delta tables and only updates when source data changes
- Use `pipelines.trigger.interval` to control how frequently each flow checks for new data
- Requires an always-running cluster — higher cost, but justified when low latency is critical

**Ideal for:** Kafka / streaming sources · IoT feeds · Live dashboards · Real-time alerting · Low-latency ETL

---

## Side-by-Side Comparison

| Dimension | ⏱ Triggered | ♾ Continuous |
|---|---|---|
| **Cluster Lifetime** | Spins up → runs → shuts down | Always on (24/7) |
| **Cost** | Lower — pay only for run time | Higher — continuous compute |
| **Data Freshness** | Only on next trigger/schedule | Near real-time |
| **Latency** | Higher (waits for trigger) | Low (processes on arrival) |
| **Best For** | Batch / scheduled ETL loads | Streaming & real-time feeds |
| **Cluster Management** | Auto-terminated after run | Manual stop required |
| **Trigger Interval** | Cron / on-demand | `pipelines.trigger.interval` |

---

## How to Choose

**Do you need near real-time data?**

- **YES → Use Continuous**
  - Kafka / streaming sources
  - IoT sensor data
  - Live dashboards
  - Real-time alerting
  - Low-latency pipelines

- **NO → Use Triggered**
  - Scheduled batch loads
  - Daily ETL jobs
  - On-demand refreshes
  - Cost-sensitive workloads
  - Dimension table updates

> 💡 **Tip:** For most pipelines, **Triggered is the recommended starting point**. Move to Continuous only when low latency is a clear business requirement.

---

## Key Takeaways

1. **Triggered = Batch** — Runs once per trigger, cluster shuts down after. Ideal for scheduled or on-demand batch workloads.
2. **Continuous = Streaming** — Always-on cluster, processes data as it arrives. Ideal for real-time and streaming use cases.
3. **Cost vs. Latency** — Triggered is more cost-efficient. Continuous offers lower latency. Choose based on your SLA needs.
4. **Start Triggered, Go Continuous When Needed** — For most pipelines, Triggered is the best default. Upgrade to Continuous only for justified low-latency requirements.

---

*Databricks Delta Live Tables — Pipeline Configuration Guide*
