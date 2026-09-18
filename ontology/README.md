# Supply Chain Ontology — AWS Context Ontology Accelerator submission bundle

Generated from the authoritative DDL in [`01_base_tables_and_data.sql`](../01_base_tables_and_data.sql)
by [`generate_ontology.py`](generate_ontology.py). The 37 classes here cover every table in that
DDL 1:1 with the 37 CSVs in [`Data/`](../Data) — this bundle is the ontology description of that
dataset, structured the way `aws/context-ontology-accelerator` (COA) actually ingests ontologies.

Note: [aws/context-ontology-accelerator](https://github.com/aws/context-ontology-accelerator) is
published as a **read-only mirror** — it does not accept pull requests. "Submitting" this bundle
means calling a deployed COA instance's Control Plane API (Scan → **Model** → Serve), not committing
a file into that repo.

## Files

| File | Purpose | COA target |
|---|---|---|
| `supply_chain.ttl` | OWL/RDFS/SKOS T-Box: 37 classes, 57 object properties (FKs), 157 datatype properties, `owl:hasKey`/cardinality restrictions, `skos:altLabel` synonyms | `POST /namespaces/{ns}/ontologies/{ontologyId}/upload` (`UploadOntology`) |
| `supply_chain_r2rml.ttl` | R2RML mapping from each class back to its Snowflake table/columns, incl. FK join conditions | `POST /namespaces/{ns}/proposals/update` (`UpdateProposal.r2rmlTurtle`) — this is what makes a class `coa:isMapped` and queryable via the VKG (Tier-2 NL→SPARQL→SQL); without it the T-Box only serves Tier-3 retrieval |
| `supply_chain_catalog.json` | Data-catalog / schema-induction input: tables, columns, types, constraints (PK/FK), synonyms, sampled distinct values | Mock data-catalog source / induction input for the `ontology-engine`, namespace `ns-asterion-supplychain` |

## Conventions (per `packages/ontology-engine/docs/ontology-data-model.md`)

- Property IRIs are `camelCase(Class)_camelCase(Column)` so identically-named columns on different
  classes never collide into one multi-domain property.
- FKs emit an `owl:ObjectProperty` in the T-Box (what the relationship *means*) and a Referencing
  Object Map in the R2RML (the actual join keys) — join keys never appear in the T-Box.
- No `owl:imports` (Ontop network-resolves imports at VKG load and fails every query in the
  namespace on a non-dereferenceable IRI) and no `coa:isMapped` (server-derived from R2RML `rr:class`
  membership; caller-supplied triples are stripped at ingest).

## Regenerating

```bash
python ontology/generate_ontology.py
```

Re-parses the DDL and rewrites all three files. Do not hand-edit them — add table/column business
names, synonyms, enums, or relationship labels to the tables in `generate_ontology.py` instead.

## Scope

Namespace: `ns-asterion-supplychain`. Datasource: `ds-scs-snowflake` (`SCS.INVENTORY` schema,
served via Athena federation — no direct Snowflake driver on the query path). Covers supplier
master and approvals, purchase orders and receipts, bills of material, work orders, inventory
snapshots, shipments with lane/carrier detail, IoT cold-chain telemetry, and quality inspections
and nonconformances. All data is synthetic.
