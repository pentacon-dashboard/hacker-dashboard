# Investment Dashboard Context

This context defines the domain language for CSV-driven PB/WM portfolio intake, client portfolio creation, and analysis readiness.

## Language

**Client Portfolio Import**:
A CSV intake outcome where normalized holdings are persisted for a selected client and become visible in that client's workspace.
_Avoid_: Customer creation, account creation

**Arbitrary Portfolio CSV**:
A financial portfolio CSV whose broker, exchange, language, column names, and field order may differ from other portfolio files.
_Avoid_: Fixed template CSV, standard upload format

**Canonical Holding**:
The normalized portfolio record used by the product after mapping source CSV columns into required holding fields.
_Avoid_: Raw CSV row, broker row

**Non-Holding Evidence**:
Source CSV data such as cash, deposits, realized PnL, or transactions that is preserved for traceability but not imported as holdings in the core flow.
_Avoid_: Holding, imported position

**Imported**:
The import state where `/upload/import` returns `status: imported` and holdings for the selected client are stored.
_Avoid_: Uploaded, analyzed

**PB Confirmation Required**:
The import state where ambiguous mapping, incomplete fields, or insufficient evidence prevents client portfolio creation.
_Avoid_: Failed customer creation, partial success

**Mapping Candidate**:
A proposed source CSV column for a portfolio field, shown to the PB when automatic mapping is uncertain.
_Avoid_: Final mapping, guessed field

**Confirmed Mapping**:
A PB-approved mapping from source CSV columns to portfolio fields that can be used for import.
_Avoid_: Inferred mapping, candidate mapping

**Column Mapping**:
A confirmed mapping where a canonical holding field reads values from a named source CSV column.
_Avoid_: Standard column requirement

**Derived Mapping**:
A confirmed mapping where a canonical holding field is filled by a deterministic source pattern instead of a source CSV column.
_Avoid_: Guess, default value

**Column-Only Correction**:
The PB confirmation behavior where the PB fixes source-to-field mappings without editing row values inside the app.
_Avoid_: Row editing, data correction

**Required Holding Field**:
A portfolio field that must be confirmed before holdings can be imported: symbol, quantity, average cost, currency, and market.
_Avoid_: Optional column, nice-to-have field

**Evidence Field**:
An optional CSV field preserved for traceability, such as source client ID, account, broker, name, or date.
_Avoid_: Required field, blocking field

**System-Confirmed Mapping**:
A mapping accepted without PB review because the source pattern is deterministic.
_Avoid_: Guess, default mapping

**Blocking Row Error**:
A row-level data error that prevents the entire import from becoming imported.
_Avoid_: Partial warning, skipped row

**Client Workspace**:
The PB-facing page for one client portfolio, including summary, holdings, and rebalance views.
_Avoid_: Customer page, account page

**CSV Intake Review**:
The pre-import validation step that inspects raw CSV structure, mapping candidates, and normalized preview.
_Avoid_: Client analysis, final analysis

**Client Portfolio Analysis**:
The post-import analysis generated from persisted holdings for one selected client.
_Avoid_: CSV analysis, upload analysis

**Import Batch**:
The set of holdings produced by one confirmed CSV import for one selected client.
_Avoid_: Upload session, portfolio

**Import Batch Audit**:
The durable record of a confirmed import batch, including source file identity, confirmed mapping, status, and warnings.
_Avoid_: Transient upload cache, UI state

**Batch Replacement**:
The behavior where re-importing the same source replaces holdings from the prior import batch without removing manually entered holdings.
_Avoid_: Append-only import, full client reset

**Import Batch Key**:
The stable identity of an import batch, composed from selected client ID, file content hash, and confirmed mapping hash.
_Avoid_: Upload ID, schema fingerprint

**Manual Holding**:
A holding entered outside the CSV import flow and therefore excluded from import batch replacement.
_Avoid_: Imported holding, batch holding

**Selected Client**:
The client chosen by the PB as the import target.
_Avoid_: CSV client, inferred client

**Source Client ID**:
A client identifier found inside the uploaded CSV and preserved as source evidence.
_Avoid_: Target client, authoritative client

## Relationships

- A **Client Portfolio Import** persists one or more holdings for exactly one selected client.
- An **Arbitrary Portfolio CSV** becomes usable only after source columns are mapped into **Canonical Holdings**.
- The core **Client Portfolio Import** target is **Canonical Holding**, not cash, deposits, realized PnL, or transactions.
- **Non-Holding Evidence** may be preserved but should not be mixed into holdings.
- An **Imported** result makes the **Client Workspace** immediately usable.
- **PB Confirmation Required** does not create a completed **Client Portfolio Import**.
- **PB Confirmation Required** can become **Imported** when the PB supplies a **Confirmed Mapping** for the same upload.
- A **Confirmed Mapping** may be a **Column Mapping** or a **Derived Mapping**.
- **Column Mapping** supports arbitrary source column names by linking them to canonical holding fields.
- **Derived Mapping** is allowed only for deterministic source patterns such as KRW-BTC, BTC/USDT, or six-digit KRX codes.
- **Column-Only Correction** can resolve mapping ambiguity, but row value errors must be fixed in the source CSV and re-uploaded.
- The **Selected Client** overrides any **Source Client ID** during import.
- **CSV Intake Review** happens before import; **Client Portfolio Analysis** happens after holdings are persisted.
- A **Client Portfolio Import** creates an **Import Batch**.
- An **Import Batch** has an **Import Batch Audit** record.
- **Batch Replacement** prevents duplicate holdings when the same CSV source is imported again for the same client.
- **Batch Replacement** must not remove holdings that were not created by the matching **Import Batch**.
- An **Import Batch** is matched by its **Import Batch Key**, not by transient upload ID or header-only schema fingerprint.
- A **Manual Holding** has no import batch key and is never removed by **Batch Replacement**.
- Every **Client Portfolio Import** requires confirmed mappings for all **Required Holding Fields**.
- **Evidence Fields** improve traceability but do not block import when absent.
- Source CSV column names may vary; the product maps aliases to canonical **Required Holding Fields** before import.
- Deterministic symbol patterns may produce **System-Confirmed Mapping** for market and currency.
- Plain US tickers such as AAPL or TSLA are not enough to infer market and currency without PB confirmation or explicit source columns.
- Any **Blocking Row Error** prevents the entire **Client Portfolio Import** from becoming **Imported**.
- Partial import is not the default success behavior.

## Example Dialogue

> **Dev:** "After a CSV upload, should we say the customer was added?"
> **Domain expert:** "Only if `/upload/import` returns `imported`, the holdings are stored under that client ID, and the client workspace can show summary, holdings, and rebalance."
>
> **Dev:** "Why does this product need a mapping review instead of one fixed CSV template?"
> **Domain expert:** "Because financial portfolio CSVs vary by broker and source; the product's job is to normalize arbitrary portfolio CSVs into canonical holdings."
>
> **Dev:** "Should the first import flow normalize cash and transaction history too?"
> **Domain expert:** "No. The core flow imports holdings only; cash, deposits, realized PnL, and transactions are preserved as non-holding evidence or handled by later canonical types."
>
> **Dev:** "If the CSV has a different client ID, should it block import?"
> **Domain expert:** "No. The PB-selected client is authoritative; preserve the CSV client ID as evidence and show a warning."
>
> **Dev:** "Should messy broker CSVs be rejected?"
> **Domain expert:** "No. Show mapping candidates and normalized preview; only persist once the PB confirms the required mappings."
>
> **Dev:** "Is analyzing the raw CSV enough?"
> **Domain expert:** "No. Real client analysis is the workspace analysis produced from persisted holdings for the selected client."
>
> **Dev:** "If the PB uploads the same CSV twice, do we append the holdings?"
> **Domain expert:** "No. Replace the matching import batch so the client portfolio does not double count holdings."
>
> **Dev:** "Can upload ID identify the import batch?"
> **Domain expert:** "No. Use selected client ID plus file content hash plus confirmed mapping hash."
>
> **Dev:** "Can batch replacement delete manually entered holdings?"
> **Domain expert:** "No. Only holdings created by the matching import batch are replaceable."
>
> **Dev:** "Can we import if the CSV calls quantity 'shares' or average cost 'purchase price'?"
> **Domain expert:** "Yes, if those source columns are confidently mapped or PB-confirmed as the required holding fields."
>
> **Dev:** "Does confirmed mapping require the CSV to use our field names?"
> **Domain expert:** "No. Confirmed mapping links arbitrary CSV column names to canonical fields, or uses derived mappings for deterministic symbol patterns."
>
> **Dev:** "If market and currency columns are missing, can symbol fill them?"
> **Domain expert:** "Only deterministic patterns can. KRW-BTC, BTC/USDT, and six-digit KRX codes are system-confirmed; plain US tickers still need PB confirmation or explicit columns."
>
> **Dev:** "Can we import 98 valid rows when 2 rows have invalid quantities?"
> **Domain expert:** "No. Block the import until the row errors are fixed or an explicit future partial-import option exists."
>
> **Dev:** "Should the PB edit broken row values in the app?"
> **Domain expert:** "No. The PB confirms column mappings only; row value errors are corrected in the source CSV and re-uploaded."

## Flagged Ambiguities

- "Customer creation" was used to mean **Client Portfolio Import**. Resolved: this product treats completion as persisted client holdings and an immediately usable workspace, not creation of a separate customer profile record.
- "client_id" may refer to the **Selected Client** or **Source Client ID**. Resolved: the **Selected Client** is authoritative for persistence; the **Source Client ID** is evidence only.
