# ADR 0014: Portfolio CSV Import Batch Replacement

**Status:** Accepted
**Date:** 2026-05-02

## Context

Financial portfolio CSV files vary by broker, exchange, language, column names, and field order. The product must normalize arbitrary portfolio CSV files into canonical holdings, but importing the same CSV for the same client twice must not double count holdings in the client workspace.

## Decision

We will store CSV import audit state in a dedicated `portfolio_import_batches` table and attach nullable import metadata to imported holdings. The import batch key is composed from `selected_client_id + file_content_hash + confirmed_mapping_hash`.

`holdings` will keep nullable `import_batch_key`, `source_row`, `source_columns`, and `source_client_id` fields. Manual holdings keep `import_batch_key = null` and are never removed by batch replacement. CSV-imported holdings with a matching import batch key are replaced when the same source and confirmed mapping are imported again for the same selected client.

## Consequences

- `/upload/import` can be idempotent for repeated CSV imports without deleting manually entered holdings.
- `/upload/csv` and `/upload/import` must preserve file content hash, confirmed mapping hash, source row, source columns, source client ID, status, and warnings as audit evidence.
- `upload_id` remains a transient cache handle and must not be used as durable import identity.
- Header-only schema fingerprints are useful for review UX but are insufficient for batch replacement.
