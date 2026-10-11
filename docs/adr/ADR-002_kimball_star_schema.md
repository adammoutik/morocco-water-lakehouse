# ADR-002: Kimball Dimensional Star Schema over One Big Table (OBT)

- **Status**: Accepted
- **Date**: 2026-10-07

## Context
Downstream consumers include executive dashboards, hydrological engineers, and ad-hoc SQL analysts. We evaluated whether to materialize a single denormalized One Big Table (OBT) or a dimensional Star Schema (`dim_reservoir`, `dim_date`, `fact_reservoir_daily`).

## Decision
We implemented a Kimball-style Star Schema using dbt Core in PostgreSQL:
1. Conformed dimension tables (`dim_reservoir`, `dim_date`) encapsulate entity metadata and calendar attributes once, avoiding repetitive string storage.
2. Fact table (`fact_reservoir_daily`) contains metrics at a strict daily observation grain with foreign keys pointing to dimension surrogate keys.
3. SQL window functions (`LAG()`) calculate drawdown velocity directly at the fact grain.

## Consequences
- **Pros**: Clear business semantics, efficient indexing, flexible slicing by dimension attributes, and compatibility with standard BI tools.
- **Cons**: Slightly higher query complexity requiring joins, handled cleanly by dbt views and documentation.
