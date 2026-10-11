# 📖 Tensift Water Reliability Lakehouse - Data Dictionary

This document details the data structures, schemas, column specifications, and relationships across the warehouse marts and staging tables.

---

## 1. Dimensional Model Overview

The warehouse layer implements a Kimball-style Star Schema optimized for analytical aggregation and time-series reporting.

```
       ┌────────────────────────┐
       │     dim_reservoir      │
       ├────────────────────────┤
       │ PK: reservoir_key (MD5)│
       │ dam_id (Natural Key)   │
       │ dam_name               │
       │ river_basin            │
       │ capacity_mm3           │
       └───────────┬────────────┘
                   │
                   │ 1:N
                   ▼
       ┌────────────────────────┐         ┌────────────────────────┐
       │  fact_reservoir_daily  │  N:1    │        dim_date        │
       ├────────────────────────┼────────►├────────────────────────┤
       │ PK: fact_key (MD5)     │         │ PK: date_key (YYYYMMDD)│
       │ FK: reservoir_key      │         │ full_date (DATE)       │
       │ FK: date_key           │         │ year (INT)             │
       │ current_volume_mm3     │         │ month (INT)            │
       │ fill_percentage        │         │ day (INT)              │
       │ daily_drawdown_rate_mm3│         │ day_of_week (INT)      │
       └────────────────────────┘         └────────────────────────┘
```

---

## 2. Table Specifications

### 2.1 `marts.dim_reservoir`
- **Granularity**: One record per monitored dam.
- **Materialization**: Table (dbt).

| Column Name | Data Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `reservoir_key` | `VARCHAR(32)` | No | Primary Key | MD5 surrogate key generated from `dam_id`. |
| `dam_id` | `VARCHAR(64)` | No | Unique | Natural identifier for the water reservoir / dam. |
| `dam_name` | `VARCHAR(128)` | No | | Normalized name of the reservoir (accents stripped). |
| `river_basin` | `VARCHAR(64)` | No | | Hydrological river basin (e.g., `Tensift`). |
| `capacity_mm3` | `NUMERIC(10,2)` | No | `> 0` | Maximum normal operating storage capacity in Mm³. |

---

### 2.2 `marts.dim_date`
- **Granularity**: One record per calendar day.
- **Materialization**: Table (dbt).

| Column Name | Data Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `date_key` | `INTEGER` | No | Primary Key | Smart integer date key in `YYYYMMDD` format. |
| `full_date` | `DATE` | No | Unique | Standard calendar date (`YYYY-MM-DD`). |
| `year` | `INTEGER` | No | | Calendar year. |
| `month` | `INTEGER` | No | `1 <= month <= 12` | Month number (1 for January to 12 for December). |
| `day` | `INTEGER` | No | `1 <= day <= 31` | Day of the month. |
| `day_of_week` | `INTEGER` | No | `0 <= dow <= 6` | Day of week index (Sunday = 0). |

---

### 2.3 `marts.fact_reservoir_daily`
- **Granularity**: One observation per reservoir per calendar day.
- **Materialization**: Table (dbt).

| Column Name | Data Type | Nullable | Constraint | Description |
|---|---|---|---|---|
| `fact_key` | `VARCHAR(32)` | No | Primary Key | MD5 surrogate hash of `(reservoir_key || '-' || date_key)`. |
| `reservoir_key` | `VARCHAR(32)` | No | Foreign Key | References `dim_reservoir.reservoir_key`. |
| `date_key` | `INTEGER` | No | Foreign Key | References `dim_date.date_key`. |
| `current_volume_mm3` | `NUMERIC(10,2)` | No | `>= 0` | Retained water volume in million cubic meters (Mm³). |
| `fill_percentage` | `NUMERIC(5,2)` | No | `0 <= pct <= 100` | Percentage of total reservoir capacity currently retained. |
| `daily_drawdown_rate_mm3` | `NUMERIC(10,3)` | Yes | | Daily volume variance ($V_t - V_{t-1}$) calculated via SQL `LAG()`. Negative values indicate net depletion. |

---

### 2.4 `staging.stg_reservoirs`
- **Granularity**: Raw ingested row from Silver Parquet layer.
- **Materialization**: View (dbt) over PostgreSQL staging table.

| Column Name | Data Type | Description |
|---|---|---|
| `dam_name` | `VARCHAR` | Dam name as normalized from CKAN bulletin. |
| `observation_date` | `DATE` | Reported observation date. |
| `capacity_mm3` | `NUMERIC` | Dam design storage capacity. |
| `reserve_volume_mm3` | `NUMERIC` | Current reported reserve volume. |
| `fill_ratio_pct` | `NUMERIC` | Fill percentage. |
| `ingested_at` | `TIMESTAMP` | Timestamp of staging ingestion. |
