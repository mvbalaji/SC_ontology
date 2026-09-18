#!/usr/bin/env python3
"""Generate the AWS Context Ontology Accelerator input bundle for the SCS supply-chain schema.

Parses the authoritative DDL in ../01_base_tables_and_data.sql and emits:

  supply_chain.ttl              OWL/RDFS/SKOS T-Box  -> UploadOntology
  supply_chain_r2rml.ttl        R2RML mapping        -> UpdateProposal.r2rmlTurtle
  supply_chain_catalog.json     CatalogTable JSON    -> mock data-catalog / induction

Conventions follow packages/ontology-engine/docs/ontology-data-model.md:
  - property IRIs are camelCase(Class)_camelCase(Column) so same-named columns
    on different classes never collide into a multi-domain property
  - FKs emit an owl:ObjectProperty in the T-Box and a Referencing Object Map in
    the R2RML; join keys live only in the R2RML
  - no owl:imports, and no coa:isMapped (server-derived, stripped at ingest)

Usage:  python generate_ontology.py
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DDL = os.path.join(HERE, "..", "01_base_tables_and_data.sql")
NS = "https://asterion.example.com/ontology/supplychain#"
DATASOURCE_ID = "ds-scs-snowflake"
SOURCE_SCHEMA = "SCS.INVENTORY"

# ---------------------------------------------------------------- business names
# table -> (ClassIRI local name, rdfs:label, skos:altLabel synonyms)
CLASSES = {
    "DIM_DATE":                 ("CalendarDate", "Calendar Date", ["date", "day", "calendar", "DIM_DATE", "time dimension"]),
    "DIM_GEO_REGION":           ("Region", "Region", ["geography", "geo region", "DIM_GEO_REGION", "world region"]),
    "DIM_GEO_COUNTRY":          ("Country", "Country", ["nation", "DIM_GEO_COUNTRY", "country of origin"]),
    "DIM_COMMODITY":            ("Commodity", "Commodity", ["category", "commodity group", "DIM_COMMODITY", "spend category"]),
    "DIM_SUB_COMMODITY":        ("SubCommodity", "Sub-Commodity", ["subcategory", "sub commodity", "DIM_SUB_COMMODITY"]),
    "DIM_CURRENCY":             ("Currency", "Currency", ["fx", "currency code", "DIM_CURRENCY"]),
    "DIM_UOM":                  ("UnitOfMeasure", "Unit of Measure", ["uom", "unit", "DIM_UOM"]),
    "DIM_INCOTERM":             ("Incoterm", "Incoterm", ["shipping terms", "trade terms", "DIM_INCOTERM", "incoterms 2020"]),
    "DIM_PORT":                 ("Port", "Port", ["seaport", "airport", "terminal", "DIM_PORT"]),
    "DIM_SUPPLIER":             ("Supplier", "Supplier", ["vendor", "supplier master", "DIM_SUPPLIER", "source", "seller"]),
    "DIM_SUPPLIER_SITE":        ("SupplierSite", "Supplier Site", ["supplier facility", "vendor site", "DIM_SUPPLIER_SITE", "manufacturing site"]),
    "DIM_MANUFACTURER":         ("Manufacturer", "Manufacturer", ["oem", "component manufacturer", "DIM_MANUFACTURER", "mfr"]),
    "DIM_PART":                 ("Part", "Part", ["component", "material", "sku", "item", "DIM_PART", "part master"]),
    "DIM_PRODUCT_FAMILY":       ("ProductFamily", "Product Family", ["product line", "family", "DIM_PRODUCT_FAMILY"]),
    "DIM_PRODUCT":              ("Product", "Product", ["finished good", "sku", "DIM_PRODUCT", "end item"]),
    "BOM_HEADER":               ("BillOfMaterials", "Bill of Materials", ["bom", "BOM_HEADER", "product structure", "recipe"]),
    "BOM_LINE":                 ("BillOfMaterialsLine", "Bill of Materials Line", ["bom line", "bom component", "BOM_LINE"]),
    "DIM_PLANT":                ("Plant", "Plant", ["factory", "manufacturing site", "DIM_PLANT", "works"]),
    "DIM_WAREHOUSE":            ("Warehouse", "Warehouse", ["dc", "distribution center", "stocking location", "DIM_WAREHOUSE"]),
    "DIM_CUSTOMER":             ("Customer", "Customer", ["account", "buyer", "DIM_CUSTOMER", "client"]),
    "DIM_CARRIER":              ("Carrier", "Carrier", ["freight forwarder", "shipping line", "DIM_CARRIER", "logistics provider"]),
    "DIM_LANE":                 ("Lane", "Lane", ["shipping lane", "trade lane", "route", "DIM_LANE", "corridor"]),
    "DIM_CONTRACT":             ("Contract", "Contract", ["supplier agreement", "DIM_CONTRACT", "purchase agreement"]),
    "SUPPLIER_PART_APPROVAL":   ("SupplierPartApproval", "Supplier Part Approval", ["approved vendor list", "avl", "asl", "approved source", "SUPPLIER_PART_APPROVAL"]),
    "PO_HEADER":                ("PurchaseOrder", "Purchase Order", ["po", "PO_HEADER", "procurement order", "purchase requisition"]),
    "PO_LINE":                  ("PurchaseOrderLine", "Purchase Order Line", ["po line", "po item", "PO_LINE"]),
    "GOODS_RECEIPT":            ("GoodsReceipt", "Goods Receipt", ["grn", "receipt", "goods received note", "GOODS_RECEIPT", "delivery"]),
    "SALES_ORDER_HEADER":       ("SalesOrder", "Sales Order", ["so", "customer order", "SALES_ORDER_HEADER", "demand"]),
    "SALES_ORDER_LINE":         ("SalesOrderLine", "Sales Order Line", ["so line", "order line", "SALES_ORDER_LINE"]),
    "SHIPMENT_HEADER":          ("Shipment", "Shipment", ["freight", "consignment", "SHIPMENT_HEADER", "load"]),
    "SHIPMENT_LINE":            ("ShipmentLine", "Shipment Line", ["shipment item", "SHIPMENT_LINE"]),
    "SHIPMENT_MILESTONE_EVENT": ("ShipmentMilestoneEvent", "Shipment Milestone Event", ["tracking event", "milestone", "shipment status event", "SHIPMENT_MILESTONE_EVENT"]),
    "IOT_SENSOR_READING":       ("SensorReading", "Sensor Reading", ["iot reading", "telemetry", "container sensor", "IOT_SENSOR_READING", "cold chain reading"]),
    "WORK_ORDER":               ("WorkOrder", "Work Order", ["wo", "production order", "manufacturing order", "WORK_ORDER"]),
    "QUALITY_INSPECTION":       ("QualityInspection", "Quality Inspection", ["incoming inspection", "iqc", "QUALITY_INSPECTION", "quality check"]),
    "NONCONFORMANCE_REPORT":    ("NonconformanceReport", "Nonconformance Report", ["ncr", "quality issue", "defect report", "NONCONFORMANCE_REPORT", "car"]),
    "FACT_INVENTORY_SNAPSHOT":  ("InventorySnapshot", "Inventory Snapshot", ["stock on hand", "inventory position", "soh", "FACT_INVENTORY_SNAPSHOT", "stock level"]),
}

# ------------------------------------------------------------------ foreign keys
# table -> {column: (parent_table, parent_column, provenance)}
# Most are implicit in the DDL (naming convention); declared explicitly here so
# the induced graph carries real relationships rather than orphan integers.
FKS = {
    "DIM_GEO_COUNTRY":          {"REGION_ID": ("DIM_GEO_REGION", "REGION_ID", "MANY_TO_ONE")},
    "DIM_SUB_COMMODITY":        {"COMMODITY_ID": ("DIM_COMMODITY", "COMMODITY_ID", "MANY_TO_ONE")},
    "DIM_PORT":                 {"COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_SUPPLIER":             {"COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE"),
                                 "COMMODITY_ID": ("DIM_COMMODITY", "COMMODITY_ID", "MANY_TO_ONE")},
    "DIM_SUPPLIER_SITE":        {"SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE"),
                                 "COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_MANUFACTURER":         {"COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_PART":                 {"COMMODITY_ID": ("DIM_COMMODITY", "COMMODITY_ID", "MANY_TO_ONE"),
                                 "SUB_COMMODITY_ID": ("DIM_SUB_COMMODITY", "SUB_COMMODITY_ID", "MANY_TO_ONE"),
                                 "UOM_CODE": ("DIM_UOM", "UOM_CODE", "MANY_TO_ONE")},
    "DIM_PRODUCT":              {"PRODUCT_FAMILY_ID": ("DIM_PRODUCT_FAMILY", "PRODUCT_FAMILY_ID", "MANY_TO_ONE")},
    "BOM_HEADER":               {"PRODUCT_ID": ("DIM_PRODUCT", "PRODUCT_ID", "MANY_TO_ONE")},
    "BOM_LINE":                 {"BOM_ID": ("BOM_HEADER", "BOM_ID", "MANY_TO_ONE"),
                                 "PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE")},
    "DIM_PLANT":                {"COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_WAREHOUSE":            {"PLANT_ID": ("DIM_PLANT", "PLANT_ID", "MANY_TO_ONE"),
                                 "COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_CUSTOMER":             {"COUNTRY_ID": ("DIM_GEO_COUNTRY", "COUNTRY_ID", "MANY_TO_ONE")},
    "DIM_LANE":                 {"ORIGIN_PORT_ID": ("DIM_PORT", "PORT_ID", "MANY_TO_ONE"),
                                 "DEST_PORT_ID": ("DIM_PORT", "PORT_ID", "MANY_TO_ONE")},
    "DIM_CONTRACT":             {"SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE"),
                                 "CURRENCY_CODE": ("DIM_CURRENCY", "CURRENCY_CODE", "MANY_TO_ONE"),
                                 "INCOTERM_CODE": ("DIM_INCOTERM", "INCOTERM_CODE", "MANY_TO_ONE")},
    "SUPPLIER_PART_APPROVAL":   {"SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE"),
                                 "SITE_ID": ("DIM_SUPPLIER_SITE", "SITE_ID", "MANY_TO_ONE"),
                                 "PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE")},
    "PO_HEADER":                {"SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE"),
                                 "PLANT_ID": ("DIM_PLANT", "PLANT_ID", "MANY_TO_ONE"),
                                 "CURRENCY_CODE": ("DIM_CURRENCY", "CURRENCY_CODE", "MANY_TO_ONE")},
    "PO_LINE":                  {"PO_ID": ("PO_HEADER", "PO_ID", "MANY_TO_ONE"),
                                 "PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE")},
    "GOODS_RECEIPT":            {"PO_LINE_ID": ("PO_LINE", "PO_LINE_ID", "MANY_TO_ONE"),
                                 "WAREHOUSE_ID": ("DIM_WAREHOUSE", "WAREHOUSE_ID", "MANY_TO_ONE")},
    "SALES_ORDER_HEADER":       {"CUSTOMER_ID": ("DIM_CUSTOMER", "CUSTOMER_ID", "MANY_TO_ONE"),
                                 "PLANT_ID": ("DIM_PLANT", "PLANT_ID", "MANY_TO_ONE")},
    "SALES_ORDER_LINE":         {"ORDER_ID": ("SALES_ORDER_HEADER", "ORDER_ID", "MANY_TO_ONE"),
                                 "PRODUCT_ID": ("DIM_PRODUCT", "PRODUCT_ID", "MANY_TO_ONE")},
    "SHIPMENT_HEADER":          {"CARRIER_ID": ("DIM_CARRIER", "CARRIER_ID", "MANY_TO_ONE"),
                                 "LANE_ID": ("DIM_LANE", "LANE_ID", "MANY_TO_ONE")},
    "SHIPMENT_LINE":            {"SHIPMENT_ID": ("SHIPMENT_HEADER", "SHIPMENT_ID", "MANY_TO_ONE"),
                                 "ORDER_LINE_ID": ("SALES_ORDER_LINE", "ORDER_LINE_ID", "MANY_TO_ONE"),
                                 "PO_LINE_ID": ("PO_LINE", "PO_LINE_ID", "MANY_TO_ONE")},
    "SHIPMENT_MILESTONE_EVENT": {"SHIPMENT_ID": ("SHIPMENT_HEADER", "SHIPMENT_ID", "MANY_TO_ONE")},
    "IOT_SENSOR_READING":       {"SHIPMENT_ID": ("SHIPMENT_HEADER", "SHIPMENT_ID", "MANY_TO_ONE")},
    "WORK_ORDER":               {"PRODUCT_ID": ("DIM_PRODUCT", "PRODUCT_ID", "MANY_TO_ONE"),
                                 "PLANT_ID": ("DIM_PLANT", "PLANT_ID", "MANY_TO_ONE")},
    "QUALITY_INSPECTION":       {"RECEIPT_ID": ("GOODS_RECEIPT", "RECEIPT_ID", "MANY_TO_ONE"),
                                 "PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE"),
                                 "SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE")},
    "NONCONFORMANCE_REPORT":    {"INSPECTION_ID": ("QUALITY_INSPECTION", "INSPECTION_ID", "MANY_TO_ONE"),
                                 "SUPPLIER_ID": ("DIM_SUPPLIER", "SUPPLIER_ID", "MANY_TO_ONE"),
                                 "PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE"),
                                 "PLANT_ID": ("DIM_PLANT", "PLANT_ID", "MANY_TO_ONE")},
    "FACT_INVENTORY_SNAPSHOT":  {"PART_ID": ("DIM_PART", "PART_ID", "MANY_TO_ONE"),
                                 "WAREHOUSE_ID": ("DIM_WAREHOUSE", "WAREHOUSE_ID", "MANY_TO_ONE"),
                                 "SNAPSHOT_DATE": ("DIM_DATE", "DATE_KEY", "MANY_TO_ONE")},
}

# ---------------------------------------------------- relationship label overrides
# (table, column) -> (rdfs:label, rdfs:comment) for object properties
REL_LABELS = {
    ("DIM_SUPPLIER", "COMMODITY_ID"):            ("supplies commodity", "Primary commodity this supplier is sourced for"),
    ("DIM_SUPPLIER", "COUNTRY_ID"):              ("located in country", "Country the supplier is headquartered in"),
    ("DIM_SUPPLIER_SITE", "SUPPLIER_ID"):        ("belongs to supplier", "Parent supplier that owns this site"),
    ("DIM_PART", "COMMODITY_ID"):                ("classified as commodity", "Top-level commodity classification of the part"),
    ("DIM_PART", "SUB_COMMODITY_ID"):            ("classified as sub-commodity", "Sub-commodity classification of the part"),
    ("DIM_PART", "UOM_CODE"):                    ("measured in", "Unit of measure the part is transacted in"),
    ("BOM_LINE", "PART_ID"):                     ("consumes part", "Component part consumed by this BOM position"),
    ("BOM_LINE", "BOM_ID"):                      ("line of BOM", "Bill of materials this line belongs to"),
    ("BOM_HEADER", "PRODUCT_ID"):                ("builds product", "Finished product this bill of materials builds"),
    ("SUPPLIER_PART_APPROVAL", "SUPPLIER_ID"):   ("approved supplier", "Supplier approved to provide the part"),
    ("SUPPLIER_PART_APPROVAL", "PART_ID"):       ("approved part", "Part the supplier is approved to provide"),
    ("SUPPLIER_PART_APPROVAL", "SITE_ID"):       ("approved at site", "Supplier site the approval is granted for"),
    ("PO_HEADER", "SUPPLIER_ID"):                ("ordered from supplier", "Supplier the purchase order was placed with"),
    ("PO_HEADER", "PLANT_ID"):                   ("ordered for plant", "Plant the purchase order is destined for"),
    ("PO_LINE", "PART_ID"):                      ("orders part", "Part being purchased on this line"),
    ("PO_LINE", "PO_ID"):                        ("line of purchase order", "Purchase order this line belongs to"),
    ("GOODS_RECEIPT", "PO_LINE_ID"):             ("receipt against PO line", "Purchase order line this receipt fulfils"),
    ("GOODS_RECEIPT", "WAREHOUSE_ID"):           ("received into warehouse", "Warehouse the goods were received into"),
    ("SALES_ORDER_HEADER", "CUSTOMER_ID"):       ("ordered by customer", "Customer that placed the sales order"),
    ("SALES_ORDER_LINE", "PRODUCT_ID"):          ("sells product", "Finished product being sold on this line"),
    ("SHIPMENT_HEADER", "CARRIER_ID"):           ("shipped by carrier", "Carrier moving the shipment"),
    ("SHIPMENT_HEADER", "LANE_ID"):              ("travels lane", "Shipping lane the shipment moves on"),
    ("DIM_LANE", "ORIGIN_PORT_ID"):              ("origin port", "Port the lane departs from"),
    ("DIM_LANE", "DEST_PORT_ID"):                ("destination port", "Port the lane arrives at"),
    ("SHIPMENT_LINE", "ORDER_LINE_ID"):          ("fulfils sales order line", "Sales order line this shipment line fulfils; null for inbound freight"),
    ("SHIPMENT_LINE", "PO_LINE_ID"):             ("fulfils purchase order line", "Purchase order line this shipment line fulfils; null for outbound freight"),
    ("IOT_SENSOR_READING", "SHIPMENT_ID"):       ("reading for shipment", "Shipment the sensor reading was captured on"),
    ("SHIPMENT_MILESTONE_EVENT", "SHIPMENT_ID"): ("milestone of shipment", "Shipment this tracking milestone belongs to"),
    ("QUALITY_INSPECTION", "RECEIPT_ID"):        ("inspects receipt", "Goods receipt that was inspected"),
    ("QUALITY_INSPECTION", "SUPPLIER_ID"):       ("inspected supplier", "Supplier whose material was inspected"),
    ("QUALITY_INSPECTION", "PART_ID"):           ("inspected part", "Part that was inspected"),
    ("NONCONFORMANCE_REPORT", "INSPECTION_ID"):  ("raised from inspection", "Inspection that triggered the NCR; null when raised in production"),
    ("NONCONFORMANCE_REPORT", "SUPPLIER_ID"):    ("supplier at fault", "Supplier held responsible for the nonconformance"),
    ("NONCONFORMANCE_REPORT", "PART_ID"):        ("nonconforming part", "Part found nonconforming"),
    ("NONCONFORMANCE_REPORT", "PLANT_ID"):       ("raised at plant", "Plant that raised the NCR"),
    ("FACT_INVENTORY_SNAPSHOT", "PART_ID"):      ("stock of part", "Part the stock position is measured for"),
    ("FACT_INVENTORY_SNAPSHOT", "WAREHOUSE_ID"): ("stock at warehouse", "Warehouse holding the stock"),
    ("FACT_INVENTORY_SNAPSHOT", "SNAPSHOT_DATE"): ("as of date", "Calendar date the snapshot was taken; join here for year, quarter and fiscal period"),
    ("WORK_ORDER", "PRODUCT_ID"):                ("produces product", "Finished product the work order builds"),
    ("WORK_ORDER", "PLANT_ID"):                  ("runs at plant", "Plant executing the work order"),
    ("DIM_CONTRACT", "SUPPLIER_ID"):             ("contracted supplier", "Supplier the contract is with"),
    ("DIM_WAREHOUSE", "PLANT_ID"):               ("attached to plant", "Plant this warehouse is attached to; null for standalone distribution centres"),
    ("DIM_GEO_COUNTRY", "REGION_ID"):            ("in region", "Geographic region the country belongs to"),
    ("DIM_SUB_COMMODITY", "COMMODITY_ID"):       ("parent commodity", "Top-level commodity this sub-commodity rolls up to"),
    ("DIM_PRODUCT", "PRODUCT_FAMILY_ID"):        ("in product family", "Product family the SKU belongs to"),
}

# ------------------------------------------------------- sampled distinct values
ENUMS = {
    ("BOM_HEADER", "BOM_VERSION"): ["A", "B", "C"],
    ("BOM_HEADER", "STATUS"): ["ACTIVE"],
    ("DIM_CARRIER", "CARRIER_MODE"): ["AIR", "MULTIMODAL", "OCEAN", "RAIL", "TRUCK"],
    ("DIM_CONTRACT", "STATUS"): ["ACTIVE"],
    ("DIM_CUSTOMER", "CUSTOMER_TIER"): ["BRONZE", "GOLD", "PLATINUM", "SILVER"],
    ("DIM_PART", "LIFECYCLE_STATUS"): ["ACTIVE", "EOL", "NRND", "OBSOLETE"],
    ("DIM_PORT", "PORT_TYPE"): ["AIR", "BOTH", "SEA"],
    ("DIM_LANE", "TRANSPORT_MODE"): ["AIR", "OCEAN"],
    ("DIM_UOM", "UOM_CODE"): ["BOX", "EA", "FT", "KG", "L", "LB", "M", "PAL", "PC", "ROL", "SET", "SHT"],
    ("DIM_INCOTERM", "INCOTERM_CODE"): ["CFR", "CIF", "CIP", "CPT", "DAP", "DDP", "DPU", "EXW", "FAS", "FCA", "FOB"],
    ("DIM_CURRENCY", "CURRENCY_CODE"): ["BRL", "CNY", "EUR", "GBP", "INR", "JPY", "KRW", "MXN", "MYR", "THB", "TWD", "USD"],
    ("DIM_DATE", "MONTH_NAME"): ["Apr", "Aug", "Dec", "Feb", "Jan", "Jul", "Jun", "Mar", "May", "Nov", "Oct", "Sep"],
    ("DIM_DATE", "DAY_NAME"): ["Fri", "Mon", "Sat", "Sun", "Thu", "Tue", "Wed"],
    ("NONCONFORMANCE_REPORT", "SEVERITY"): ["CRITICAL", "MAJOR", "MINOR"],
    ("NONCONFORMANCE_REPORT", "DISPOSITION"): ["RETURN", "REWORK", "SCRAP", "USE_AS_IS"],
    ("NONCONFORMANCE_REPORT", "STATUS"): ["CLOSED", "OPEN"],
    ("NONCONFORMANCE_REPORT", "ROOT_CAUSE"): [
        "Cracked substrate from shock", "Dimensional out-of-spec", "Documentation mismatch",
        "ESD damage in shipping", "Electrical test failure", "Material contamination",
        "Solder joint defect", "Surface finish degradation", "Unapproved substitution",
        "Wrong revision shipped"],
    ("PO_HEADER", "STATUS"): ["CANCELLED", "OPEN", "PARTIAL", "RECEIVED"],
    ("QUALITY_INSPECTION", "RESULT"): ["CONDITIONAL", "FAIL", "PASS"],
    ("SALES_ORDER_HEADER", "STATUS"): ["OPEN", "PARTIAL", "SHIPPED"],
    ("SHIPMENT_HEADER", "STATUS"): ["DELAYED", "DELIVERED", "IN_TRANSIT"],
    ("SHIPMENT_MILESTONE_EVENT", "MILESTONE"): [
        "ARRIVED_PORT", "BOOKING_CONFIRMED", "CUSTOMS_CLEARANCE", "DELIVERED", "DEPARTED",
        "GATE_IN", "GATE_OUT", "INVOICE_SENT", "IN_TRANSIT", "LOADED", "OUT_FOR_DELIVERY",
        "PICKED_UP", "POD_SIGNED", "TRANSSHIPMENT"],
    ("SUPPLIER_PART_APPROVAL", "STATUS"): ["APPROVED"],
    ("WORK_ORDER", "STATUS"): ["COMPLETED", "IN_PROGRESS", "ON_HOLD"],
}

# --------------------------------------------------------- column-level synonyms
COL_SYNONYMS = {
    ("DIM_SUPPLIER", "RELIABILITY_RATING"): ["reliability", "supplier score", "otd rating"],
    ("DIM_SUPPLIER", "IS_PROBLEM"): ["problem supplier", "at risk supplier", "flagged supplier"],
    ("DIM_SUPPLIER_SITE", "LEAD_TIME_DAYS"): ["lead time", "replenishment lead time"],
    ("DIM_PART", "UNIT_COST_USD"): ["standard cost", "part cost", "unit cost"],
    ("DIM_PART", "LIFECYCLE_STATUS"): ["lifecycle", "eol status", "part status"],
    ("DIM_PRODUCT", "UNIT_PRICE_USD"): ["list price", "selling price"],
    ("GOODS_RECEIPT", "DAYS_VARIANCE"): ["delivery variance", "days late", "schedule variance", "otd variance"],
    ("QUALITY_INSPECTION", "PPM"): ["defect rate", "parts per million", "ppm defect rate"],
    ("QUALITY_INSPECTION", "DEFECT_COUNT"): ["defects", "rejects"],
    ("FACT_INVENTORY_SNAPSHOT", "ON_HAND_QTY"): ["stock on hand", "soh", "on hand quantity", "inventory quantity"],
    ("FACT_INVENTORY_SNAPSHOT", "ON_HAND_VALUE"): ["inventory value", "stock value", "tied up capital"],
    ("FACT_INVENTORY_SNAPSHOT", "DOI"): ["days of inventory", "days of supply", "dos", "coverage days"],
    ("FACT_INVENTORY_SNAPSHOT", "DAILY_USAGE_QTY"): ["daily usage", "consumption rate", "burn rate"],
    ("PO_LINE", "UNIT_PRICE"): ["po price", "purchase price"],
    ("BOM_LINE", "QUANTITY_PER"): ["qty per", "usage per assembly", "quantity per assembly"],
    ("DIM_LANE", "TRANSIT_DAYS_AVG"): ["transit time", "average transit days"],
    ("IOT_SENSOR_READING", "BREACH_FLAG"): ["breach", "excursion", "threshold breach", "cold chain breach"],
    ("IOT_SENSOR_READING", "TEMPERATURE_C"): ["temperature", "temp"],
    ("DIM_CUSTOMER", "CUSTOMER_TIER"): ["tier", "segment", "customer segment"],
}

SQL_TO_XSD = {
    "INT": "xsd:integer", "BIGINT": "xsd:long", "SMALLINT": "xsd:short",
    "TINYINT": "xsd:byte", "FLOAT": "xsd:float", "DOUBLE": "xsd:double",
    "DECIMAL": "xsd:decimal", "NUMERIC": "xsd:decimal", "VARCHAR": "xsd:string",
    "TEXT": "xsd:string", "CHAR": "xsd:string", "STRING": "xsd:string",
    "BOOLEAN": "xsd:boolean", "DATE": "xsd:date", "TIMESTAMP": "xsd:dateTime",
    "TIMESTAMP_NTZ": "xsd:dateTime", "DATETIME": "xsd:dateTime", "TIME": "xsd:time",
}


def camel(s):
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", s) if p]
    if not parts:
        return "value"
    head = parts[0].lower()
    return head + "".join(p.capitalize() for p in parts[1:])


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def parse_ddl(path):
    """Return ordered list of {name, comment, columns:[...]} from the Snowflake DDL."""
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()
    tables = []
    pattern = re.compile(
        r"CREATE OR REPLACE TABLE\s+SCS\.INVENTORY\.(\w+)\s*\((.*?)\)\s*COMMENT\s*=\s*'([^']*)'",
        re.S,
    )
    for m in pattern.finditer(sql):
        name, body, tcomment = m.group(1), m.group(2), m.group(3)
        cols = []
        for raw in body.split("\n"):
            line = raw.strip().rstrip(",").strip()
            if not line or line.startswith("--"):
                continue
            cm = re.match(r"^(\w+)\s+([A-Z_]+)(?:\(([\d,\s]+)\))?(.*)$", line)
            if not cm:
                continue
            col, sqltype, args, rest = cm.group(1), cm.group(2), cm.group(3), cm.group(4)
            if sqltype in ("PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE"):
                continue
            ccomment = None
            ccm = re.search(r"COMMENT\s+'([^']*)'", rest)
            if ccm:
                ccomment = ccm.group(1)
            length = precision = scale = None
            if args:
                nums = [int(x) for x in args.replace(" ", "").split(",") if x]
                if sqltype in ("DECIMAL", "NUMERIC"):
                    precision = nums[0]
                    scale = nums[1] if len(nums) > 1 else 0
                else:
                    length = nums[0]
            cols.append({
                "name": col,
                "sqltype": sqltype,
                "length": length,
                "precision": precision,
                "scale": scale,
                "not_null": "NOT NULL" in rest.upper() or "NOT NULL" in line.upper(),
                "pk": "PRIMARY KEY" in line.upper(),
                "comment": ccomment,
            })
        tables.append({"name": name, "comment": tcomment, "columns": cols})
    return tables


def prop_iri(cls_local, col):
    return "%s_%s" % (camel(cls_local), camel(col))


def build_turtle(tables):
    L = []
    w = L.append
    w("# Supply Chain Ontology — Asterion Devices (synthetic)")
    w("# Generated by generate_ontology.py from 01_base_tables_and_data.sql. Do not hand-edit.")
    w("#")
    w("# Target: AWS Context Ontology Accelerator")
    w("#   POST /namespaces/{ns}/ontologies/{ontologyId}/upload")
    w("#")
    w("# Conventions (packages/ontology-engine/docs/ontology-data-model.md):")
    w("#   - owl:imports is never emitted: Ontop network-resolves imports at VKG load")
    w("#     and fails every query in the namespace on a non-dereferenceable IRI.")
    w("#   - coa:isMapped is never emitted: it is server-derived from R2RML rr:class")
    w("#     membership and caller-supplied triples are stripped at ingest.")
    w("#   - FK join keys live only in the R2RML; the T-Box carries what the")
    w("#     relationship means (domain, range, coa:fkProvenance).")
    w("")
    w("@prefix owl:  <http://www.w3.org/2002/07/owl#> .")
    w("@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    w("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    w("@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .")
    w("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    w("@prefix coa:  <http://coa.amazon.com/vocab/coa#> .")
    w("@prefix sc:   <%s> ." % NS)
    w("")
    w("<%s> a owl:Ontology ;" % NS.rstrip("#"))
    w('    rdfs:label "Asterion Supply Chain Ontology" ;')
    w('    rdfs:comment "Electronics manufacturing supply chain: sourcing, procurement, '
      'inbound quality, manufacturing, inventory, logistics and demand. Induced from the '
      'SCS.INVENTORY Snowflake schema — 37 tables covering supplier master and approvals, '
      'purchase orders and receipts, bills of material, work orders, inventory snapshots, '
      'shipments with lane and carrier detail, IoT cold-chain telemetry, and quality '
      'inspections and nonconformances. All data is synthetic." ;')
    w('    owl:versionInfo "1.0.0" .')
    w("")

    # ---- classes
    for t in tables:
        if t["name"] not in CLASSES:
            continue
        local, label, syns = CLASSES[t["name"]]
        w("#" + "-" * 76)
        w("# %s  <-  %s.%s" % (local, SOURCE_SCHEMA, t["name"]))
        w("#" + "-" * 76)
        w("")
        lines = ["sc:%s a owl:Class ;" % local,
                 '    rdfs:label "%s" ;' % esc(label),
                 '    rdfs:comment "%s" ;' % esc(t["comment"])]
        for s in syns:
            lines.append('    skos:altLabel "%s" ;' % esc(s))
        pks = [c["name"] for c in t["columns"] if c["pk"]]
        if pks:
            key_props = ", ".join("sc:%s" % prop_iri(local, p) for p in pks)
            lines.append("    owl:hasKey ( %s ) ;" % key_props)
        # cardinality restrictions from NOT NULL / PRIMARY KEY
        restr = []
        for c in t["columns"]:
            p = "sc:%s" % prop_iri(local, c["name"])
            if c["pk"]:
                restr.append("        [ a owl:Restriction ; owl:onProperty %s ; "
                             'owl:cardinality "1"^^xsd:nonNegativeInteger ]' % p)
            elif c["not_null"]:
                restr.append("        [ a owl:Restriction ; owl:onProperty %s ; "
                             'owl:minCardinality "1"^^xsd:nonNegativeInteger ]' % p)
        if restr:
            lines.append("    rdfs:subClassOf")
            lines.append(" ,\n".join(restr) + " ;")
        lines[-1] = lines[-1].rstrip(" ;") + " ."
        w("\n".join(lines))
        w("")

        fks = FKS.get(t["name"], {})
        for c in t["columns"]:
            pname = prop_iri(local, c["name"])
            if c["name"] in fks:
                parent_t, parent_c, prov = fks[c["name"]]
                parent_local = CLASSES[parent_t][0]
                rl, rc = REL_LABELS.get(
                    (t["name"], c["name"]),
                    (camel(c["name"]),
                     "Foreign key: %s.%s references %s.%s" % (t["name"], c["name"], parent_t, parent_c)))
                w("sc:%s a owl:ObjectProperty ;" % pname)
                w('    rdfs:label "%s" ;' % esc(rl))
                w('    rdfs:comment "%s" ;' % esc(rc))
                w("    rdfs:domain sc:%s ;" % local)
                w("    rdfs:range sc:%s ;" % parent_local)
                w('    coa:fkProvenance "%s" .' % prov)
                w("")
            else:
                xsd = SQL_TO_XSD.get(c["sqltype"], "xsd:string")
                w("sc:%s a owl:DatatypeProperty ;" % pname)
                w('    rdfs:label "%s" ;' % esc(c["name"]))
                comment = c["comment"] or "%s.%s" % (t["name"], c["name"])
                w('    rdfs:comment "%s" ;' % esc(comment))
                w("    rdfs:domain sc:%s ;" % local)
                for s in COL_SYNONYMS.get((t["name"], c["name"]), []):
                    w('    skos:altLabel "%s" ;' % esc(s))
                for v in ENUMS.get((t["name"], c["name"]), []):
                    w('    coa:distinctValues "%s" ;' % esc(v))
                w("    rdfs:range %s ." % xsd)
                w("")
    return "\n".join(L) + "\n"


def sql_ident(name):
    """SQL-delimited identifier, per the accelerator's sql_ident.

    Every table and column in SCS.INVENTORY is plain uppercase with underscores —
    no spaces, mixed case or reserved words — so unquoted identifiers resolve
    correctly in Snowflake and keep the Turtle literal readable. Wrap in double
    quotes here if the schema ever gains an identifier that needs delimiting.
    """
    return name


def build_r2rml(tables):
    L = []
    w = L.append
    w("# R2RML mapping — Asterion Supply Chain -> SCS.INVENTORY (Snowflake)")
    w("# Generated by generate_ontology.py. Do not hand-edit.")
    w("#")
    w("# Target: POST /namespaces/{ns}/proposals/update  with r2rmlTurtle")
    w("# This is what makes classes coa:isMapped and therefore answerable by")
    w("# Tier-2 structured (NL->SPARQL->SQL) queries. Without it, an uploaded")
    w("# T-Box serves Tier-3 retrieval only.")
    w("")
    w("@prefix rr:   <http://www.w3.org/ns/r2rml#> .")
    w("@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .")
    w("@prefix coa:  <http://coa.amazon.com/vocab/coa#> .")
    w("@prefix sc:   <%s> ." % NS)
    w("")
    for t in tables:
        if t["name"] not in CLASSES:
            continue
        local = CLASSES[t["name"]][0]
        pks = [c["name"] for c in t["columns"] if c["pk"]]
        if not pks:
            continue
        tmpl = "/".join("{%s}" % p for p in pks)
        w("sc:TriplesMap_%s" % local)
        w('    rr:logicalTable [ rr:tableName "%s.%s" ] ;'
          % (SOURCE_SCHEMA, sql_ident(t["name"])))
        w("    rr:subjectMap [")
        w('        rr:template "%s%s/%s" ;' % (NS.rstrip("#") + "/", local.lower(), tmpl))
        w("        rr:class sc:%s ;" % local)
        w("    ] ;")
        w('    coa:datasourceId "%s" ;' % DATASOURCE_ID)
        w('    coa:sourceSchema "%s" ;' % SOURCE_SCHEMA)
        fks = FKS.get(t["name"], {})
        poms = []
        for c in t["columns"]:
            pname = prop_iri(local, c["name"])
            if c["name"] in fks:
                parent_t, parent_c, _ = fks[c["name"]]
                parent_local = CLASSES[parent_t][0]
                poms.append(
                    "    rr:predicateObjectMap [\n"
                    "        rr:predicate sc:%s ;\n"
                    "        rr:objectMap [\n"
                    "            rr:parentTriplesMap sc:TriplesMap_%s ;\n"
                    '            rr:joinCondition [ rr:child "%s" ; rr:parent "%s" ] ;\n'
                    "        ] ;\n"
                    "    ]" % (pname, parent_local, c["name"], parent_c))
            else:
                xsd = SQL_TO_XSD.get(c["sqltype"], "xsd:string")
                poms.append(
                    "    rr:predicateObjectMap [\n"
                    "        rr:predicate sc:%s ;\n"
                    '        rr:objectMap [ rr:column "%s" ; rr:datatype %s ] ;\n'
                    "    ]" % (pname, c["name"], xsd))
        w(" ;\n".join(poms) + " .")
        w("")
    return "\n".join(L) + "\n"


def build_catalog(tables):
    sources = []
    tbls = []
    for t in tables:
        if t["name"] not in CLASSES:
            continue
        local, label, syns = CLASSES[t["name"]]
        fks = FKS.get(t["name"], {})
        cols = []
        for c in t["columns"]:
            sqltype = c["sqltype"]
            # TIMESTAMP_NTZ is not in the accelerator's _SQL_TO_XSD map and would
            # silently fall through to xsd:string; declare it as TIMESTAMP.
            if sqltype == "TIMESTAMP_NTZ":
                sqltype = "TIMESTAMP"
            entry = {
                "name": c["name"],
                "dataType": sqltype,
                "description": c["comment"] or "",
                "constraint": "PRIMARY_KEY" if c["pk"] else ("NOT_NULL" if c["not_null"] else "NULL"),
                "ordinalPosition": len(cols) + 1,
            }
            if c["length"]:
                entry["dataLength"] = c["length"]
            if c["precision"]:
                entry["precision"] = c["precision"]
                entry["scale"] = c["scale"]
            syn = COL_SYNONYMS.get((t["name"], c["name"]), [])
            if syn:
                entry["synonyms"] = syn
            dv = ENUMS.get((t["name"], c["name"]), [])
            if dv:
                entry["distinctValues"] = dv
            cols.append(entry)

        constraints = []
        pks = [c["name"] for c in t["columns"] if c["pk"]]
        if pks:
            constraints.append({"constraintType": "PRIMARY_KEY", "columns": pks})
        for col, (pt, pc, prov) in fks.items():
            # referredColumns must be a dotted TABLE.COLUMN pair: a single-segment
            # value carries no column, and build_r2rml would then emit a bare
            # rr:parentTriplesMap, producing a Cartesian product (R2RML 7.5).
            constraints.append({
                "constraintType": "FOREIGN_KEY",
                "columns": [col],
                "referredColumns": ["%s.%s" % (pt, pc)],
                "relationshipType": prov,
            })
        tbls.append({
            "id": "%s.%s" % (SOURCE_SCHEMA, t["name"]),
            "name": t["name"],
            "fullyQualifiedName": "SCS.INVENTORY.%s" % t["name"],
            "description": t["comment"],
            "synonyms": [label] + syns,
            "datasourceId": DATASOURCE_ID,
            "sourceSchema": SOURCE_SCHEMA,
            "columns": cols,
            "tableConstraints": constraints,
        })
    sources.append({
        "datasourceId": DATASOURCE_ID,
        "sourceType": "JDBC_DATABASE",
        "databases": [{
            "name": "SCS",
            "description": "Asterion Devices synthetic supply-chain warehouse. Snowflake; "
                           "serve path is Athena-federated (no direct-SQL driver for Snowflake).",
            "tables": tbls,
        }],
    })
    return {"namespaceId": "ns-asterion-supplychain", "sources": sources}


def main():
    tables = parse_ddl(DDL)
    known = [t for t in tables if t["name"] in CLASSES]
    print("parsed %d tables from DDL, %d mapped to classes" % (len(tables), len(known)))
    missing = set(CLASSES) - {t["name"] for t in tables}
    if missing:
        raise SystemExit("CLASSES references tables absent from the DDL: %s" % sorted(missing))

    out = {
        "supply_chain.ttl": build_turtle(tables),
        "supply_chain_r2rml.ttl": build_r2rml(tables),
        "supply_chain_catalog.json": json.dumps(build_catalog(tables), indent=2) + "\n",
    }
    for fname, content in out.items():
        path = os.path.join(HERE, fname)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("wrote %-28s %8d bytes" % (fname, len(content)))

    ncls = len(known)
    nobj = sum(len(FKS.get(t["name"], {})) for t in known)
    ndat = sum(len(t["columns"]) - len(FKS.get(t["name"], {})) for t in known)
    print("classes=%d objectProperties=%d datatypeProperties=%d" % (ncls, nobj, ndat))


if __name__ == "__main__":
    main()
