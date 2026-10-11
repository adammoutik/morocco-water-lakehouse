# ADR-001: Medallion Architecture on MinIO S3 and Apache Parquet

- **Status**: Accepted
- **Date**: 2026-10-05

## Context
The Tensift Water Reliability platform ingests diverse upstream data streams: semi-structured Excel bulletins from government portals and high-frequency JSON from Open-Meteo APIs. Ingesting directly into a relational database creates tight coupling and risks data loss when schema changes occur.

## Decision
We adopted the Databricks Medallion Architecture pattern backed by MinIO S3 object storage:
1. **Bronze**: Raw immutable storage with cryptographic SHA-256 fingerprinting. No schema transformations are applied.
2. **Silver**: Cleaned and validated data stored as columnar Snappy-compressed Apache Parquet. Accents are normalized, footer aggregates are stripped, and timestamps are standardized.
3. **Gold**: High-performance joined datasets for downstream analytics and Kimball-modeled warehouse tables.

## Consequences
- **Pros**: Clear lineage, safe reprocessing from raw bronze files, cost-effective columnar storage, fault isolation.
- **Cons**: Requires intermediate orchestration steps between object storage and database staging.
