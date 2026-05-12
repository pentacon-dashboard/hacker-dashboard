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

**Position**:
The minimum client portfolio fact that a client holds a quantity of a symbol in a market. A position can exist without cost basis.
_Avoid_: Fully valued holding, raw CSV row

**Cost Basis**:
The acquisition-cost evidence for a position, such as average cost, purchase amount, or book cost. Cost basis may be missing.
_Avoid_: Current price, inferred profit

**Cost Basis Status**:
The status of cost basis evidence for a persisted position: provided, missing, derived, or needs review.
_Avoid_: Fake zero cost, implicit completeness

**Enriched Holding**:
A position combined with market price, optional cost basis, and deterministic metrics for dashboard rendering.
_Avoid_: Raw position, guaranteed complete metrics

**Non-Holding Evidence**:
Source CSV data such as cash, deposits, realized PnL, or transactions that is preserved for traceability but not imported as holdings in the core flow.
_Avoid_: Holding, imported position

**Imported**:
The import state where every importable source row was persisted and no recoverable or quarantined rows remain.
_Avoid_: Uploaded, analyzed

**Partial Imported**:
The import state where at least one source row was persisted and at least one source row remains recoverable, quarantined, or excluded as garbage.
_Avoid_: Failed import, complete import

**PB Confirmation Required**:
The import state where ambiguous mapping, incomplete fields, or insufficient evidence prevents client portfolio creation.
_Avoid_: Failed customer creation, partial success

**Mapping Candidate**:
A proposed source CSV column for a portfolio field, shown to the PB when automatic mapping is uncertain.
_Avoid_: Final mapping, guessed field

**AI Semantic Mapper**:
An LLM-assisted mapper that inspects sanitized CSV structure, sample rows, and value-pattern summaries to propose column mappings, CSV kind, row classification rules, and risk flags.
_Avoid_: Import executor, source of truth

**Structured Mapping Output**:
The strict schema-bound JSON output produced by the AI Semantic Mapper. It must be validated before any mapping or row classification is used.
_Avoid_: Free-form AI explanation, unvalidated prompt response

**Confirmed Mapping**:
A PB-approved mapping from source CSV columns to portfolio fields that can be used for import.
_Avoid_: Inferred mapping, candidate mapping

**Schema Profile**:
A reusable identity for a CSV format based on column names, column order, value-pattern summary, source hints, confirmed mapping, AI mapper version, and verifier version.
_Avoid_: File content hash, one-off upload ID

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
A portfolio field that must be confirmed before legacy canonical holdings can be imported: symbol, quantity, average cost, currency, and market.
_Avoid_: Optional column, nice-to-have field

**Evidence Field**:
An optional CSV field preserved for traceability, such as source client ID, account, broker, name, or date.
_Avoid_: Required field, blocking field

**System-Confirmed Mapping**:
A mapping accepted without PB review because the source pattern is deterministic.
_Avoid_: Guess, default mapping

**Blocking Row Error**:
A row-level data error that prevents that row from becoming an imported position or holding. It does not block unrelated valid rows in AI-assisted partial import.
_Avoid_: Partial warning, skipped row

**Partial Import**:
An import outcome where valid rows are persisted while recoverable, quarantined, or garbage rows are reported separately with source-row evidence.
_Avoid_: All-or-nothing import, silent skip

**Recoverable Row**:
A source row with enough meaning to preserve for PB review, but not enough verified evidence to persist as a position or holding.
_Avoid_: Garbage row, imported row

**Quarantined Row**:
A source row that may represent financial data but is unsafe to import because required values are invalid, contradictory, or unsupported.
_Avoid_: Imported row, deleted row

**Garbage Row**:
A source row excluded from financial import because it is a blank row, subtotal, repeated header, note, disclosure, or otherwise not portfolio data.
_Avoid_: Invalid holding, recoverable row

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

**Import Row Ledger**:
The durable row-level audit record for an import batch. It records each source row's status, raw row evidence, normalized payload, reason codes, and any linked imported holding or position.
_Avoid_: Upload cache, UI-only review state

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
- A **Position** requires symbol, quantity, and market; **Cost Basis** is separate and may be absent.
- The existing holdings table may physically store both **Position** and optional **Cost Basis** data; domain language still distinguishes them.
- A missing **Cost Basis** must be represented as missing/null with **Cost Basis Status**, never as zero.
- An **Enriched Holding** may degrade profit, loss, return, and rebalance evidence when **Cost Basis** is missing.
- **Non-Holding Evidence** may be preserved but should not be mixed into holdings.
- An **Imported** result makes the **Client Workspace** immediately usable.
- A **Partial Imported** result also makes the **Client Workspace** usable, but the upload review must show which rows were not imported.
- **PB Confirmation Required** does not create a completed **Client Portfolio Import**.
- **PB Confirmation Required** can become **Imported** when the PB supplies a **Confirmed Mapping** for the same upload.
- A **Confirmed Mapping** may be a **Column Mapping** or a **Derived Mapping**.
- A **Confirmed Mapping** can be reused through a **Schema Profile** when a later CSV has the same source structure and passes deterministic verification.
- **Column Mapping** supports arbitrary source column names by linking them to canonical holding fields.
- **Derived Mapping** is allowed only for deterministic source patterns such as KRW-BTC, BTC/USDT, or six-digit KRX codes.
- **Column-Only Correction** can resolve mapping ambiguity, but row value errors must be fixed in the source CSV and re-uploaded.
- The **Selected Client** overrides any **Source Client ID** during import.
- **CSV Intake Review** happens before import; **Client Portfolio Analysis** happens after holdings are persisted.
- A **Client Portfolio Import** creates an **Import Batch**.
- An **Import Batch** has an **Import Batch Audit** record.
- An **Import Batch** also has an **Import Row Ledger** when partial import, recoverable rows, quarantined rows, or garbage rows are present.
- The **Import Row Ledger** must outlive the transient upload cache so PB review remains possible after the browser session or 30-minute upload cache expires.
- **Batch Replacement** prevents duplicate holdings when the same CSV source is imported again for the same client.
- **Batch Replacement** must not remove holdings that were not created by the matching **Import Batch**.
- An **Import Batch** is matched by its **Import Batch Key**, not by transient upload ID or header-only schema fingerprint.
- A **Schema Profile** is matched by source structure and verification metadata, not by exact file content hash.
- A **Manual Holding** has no import batch key and is never removed by **Batch Replacement**.
- Every **Client Portfolio Import** requires confirmed mappings for all **Required Holding Fields**.
- **Evidence Fields** improve traceability but do not block import when absent.
- Source CSV column names may vary; the product maps aliases to canonical **Required Holding Fields** before import.
- The **AI Semantic Mapper** may propose mappings only through **Structured Mapping Output**.
- **Structured Mapping Output** is never sufficient by itself to persist client data; deterministic verification and, when needed, PB confirmation still decide import.
- If the **AI Semantic Mapper** is unavailable or returns invalid **Structured Mapping Output**, deterministic mapping and PB confirmation flow must still work.
- Deterministic symbol patterns may produce **System-Confirmed Mapping** for market and currency.
- Plain US tickers such as AAPL or TSLA are not enough to infer market and currency without PB confirmation or explicit source columns.
- A **Blocking Row Error** blocks only the affected source row in AI-assisted partial import.
- **Partial Import** is the default target for AI-assisted intake: import valid rows and separately report recoverable, quarantined, and garbage rows.
- Future AI-assisted intake should prefer importing valid **Positions** over fabricating missing **Cost Basis**.
- AI-assisted intake status vocabulary is **Imported**, **Partial Imported**, **PB Confirmation Required**, **Insufficient Data**, and **Failed**.
- AI-assisted intake requires durable schema support for optional **Cost Basis**, **Import Row Ledger**, and reusable **Schema Profile** records.

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
> **Domain expert:** "Yes in AI-assisted partial import. Persist the 98 valid rows, quarantine the 2 invalid rows with source-row evidence, and show the PB what was not imported."
>
> **Dev:** "Should that return the same status as a fully clean import?"
> **Domain expert:** "No. Use Partial Imported so the workspace can open while the review UI still shows unresolved rows."
>
> **Dev:** "Can recoverable and quarantined rows live only in the upload cache?"
> **Domain expert:** "No. Persist them in an Import Row Ledger so row-level review, evidence, and audit survive beyond the transient upload session."
>
> **Dev:** "Should a confirmed mapping apply only to the exact same uploaded file?"
> **Domain expert:** "No. Reuse it through a Schema Profile for later files with the same structure, then re-run deterministic verification on all rows."
>
> **Dev:** "Can the AI mapper return free-form text that the backend interprets?"
> **Domain expert:** "No. It must return Structured Mapping Output that passes schema validation before deterministic verification uses it."
>
> **Dev:** "Should CSV import fail when the AI mapper is unavailable?"
> **Domain expert:** "No. Fall back to deterministic mapping and PB confirmation; AI accelerates mapping but is not required for the core import flow."
>
> **Dev:** "Can AI-assisted partial import be implemented only with transient API response state?"
> **Domain expert:** "No. It needs durable schema support so positions with missing cost basis, row-level review state, and reusable schema profiles survive reloads and future imports."
>
> **Dev:** "Should the PB edit broken row values in the app?"
> **Domain expert:** "No. The PB confirms column mappings only; row value errors are corrected in the source CSV and re-uploaded."
>
> **Dev:** "Can we keep a row when it has symbol and quantity but no average cost?"
> **Domain expert:** "Yes as a Position, but not as a fully evidenced Enriched Holding. Profit, loss, return, and cost-basis-dependent analysis must degrade until Cost Basis is supplied."
>
> **Dev:** "Should we create a separate physical positions table immediately?"
> **Domain expert:** "No. Extend the existing holdings table to allow missing cost basis and record Cost Basis Status, while keeping the domain distinction clear."

## Flagged Ambiguities

- "Customer creation" was used to mean **Client Portfolio Import**. Resolved: this product treats completion as persisted client holdings and an immediately usable workspace, not creation of a separate customer profile record.
- "client_id" may refer to the **Selected Client** or **Source Client ID**. Resolved: the **Selected Client** is authoritative for persistence; the **Source Client ID** is evidence only.
- "Holding" was used for both minimum position facts and fully costed dashboard holdings. Resolved: use **Position** for symbol/quantity/market, **Cost Basis** for acquisition-cost evidence, and **Enriched Holding** for dashboard-ready records.
- "Blocking Row Error" previously implied all-or-nothing import. Resolved: AI-assisted intake uses **Partial Import** by default, so row errors block only affected rows.
