-- =============================================================================
-- deploy_production.sql
-- Full deployment script for Supply Chain Knowledge Graph
-- Target: new Snowflake production instance
--
-- EXECUTION ORDER:
--   Part 1: Roles & Grants (run as ACCOUNTADMIN / SECURITYADMIN)
--   Part 2: Database & Schemas (run as SYSADMIN)
--   Part 3: Base Tables & Data (run as SUPPLYCHAIN) — sources 01_base_tables_and_data.sql
--   Part 4: KG Tables & Data (run as SUPPLYCHAIN)
--   Part 5: KG Views (run as SUPPLYCHAIN)
--   Part 6: Document Corpus (run as SUPPLYCHAIN)
--   Part 7: Semantic View (run as SUPPLYCHAIN)
--   Part 8: Cortex Search Service (run as SUPPLYCHAIN)
--   Part 9: Cortex Agents (run as SUPPLYCHAIN)
--   Part 10: AI & Cross-role Grants (run as ACCOUNTADMIN)
--
-- PREREQUISITES:
--   - A warehouse named COMPUTE_WH (or change all references)
--   - Run each section with the indicated role
-- =============================================================================


-- =============================================================================
-- PART 1: ROLES & GRANTS
-- =============================================================================
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS SUPPLYCHAIN
  COMMENT = 'Owner role for supply chain KG objects';
CREATE ROLE IF NOT EXISTS GE_MCP_ROLE
  COMMENT = 'MCP integration role';

GRANT ROLE SUPPLYCHAIN TO ROLE SYSADMIN;
GRANT ROLE SUPPLYCHAIN TO ROLE ACCOUNTADMIN;

-- GE_MCP_ROLE inherits from SUPPLYCHAIN
GRANT USAGE ON ROLE SUPPLYCHAIN TO ROLE GE_MCP_ROLE;

USE ROLE ACCOUNTADMIN;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SUPPLYCHAIN;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE GE_MCP_ROLE;


-- =============================================================================
-- PART 2: DATABASE & SCHEMAS
-- =============================================================================
USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS SCS
  COMMENT = 'Supply Chain Knowledge Graph';

GRANT OWNERSHIP ON DATABASE SCS TO ROLE SUPPLYCHAIN;

USE ROLE SUPPLYCHAIN;
USE WAREHOUSE COMPUTE_WH;

CREATE SCHEMA IF NOT EXISTS SCS.INVENTORY
  COMMENT = 'Base dimension and fact tables';
CREATE SCHEMA IF NOT EXISTS SCS.KG
  COMMENT = 'Knowledge graph nodes, edges, and graph analytics';
CREATE SCHEMA IF NOT EXISTS SCS.SEMANTIC
  COMMENT = 'Semantic views and agent configuration';


-- =============================================================================
-- PART 3: BASE TABLES & DATA
-- Run the full 01_base_tables_and_data.sql script here.
-- It is self-contained (uses GENERATOR for synthetic data).
-- =============================================================================
-- >>> EXECUTE FILE: 01_base_tables_and_data.sql <<<


-- =============================================================================
-- PART 4: KG TABLES & DATA
-- Option A: If migrating from same cloud region, use data sharing or replication
-- Option B: Export to stage from source, import on target (shown below)
-- =============================================================================
USE ROLE SUPPLYCHAIN;
USE WAREHOUSE COMPUTE_WH;

-- 4a. Create tables
CREATE OR REPLACE TABLE SCS.KG.KG_NODES (
    NODE_ID         NUMBER(38,0) NOT NULL,
    NODE_TYPE       VARCHAR(30)  NOT NULL COMMENT 'Entity class: SUPPLIER, PART, PRODUCT, PLANT, etc.',
    SOURCE_ID       NUMBER(38,0) NOT NULL COMMENT 'PK from the source dimension table',
    LABEL           VARCHAR(300) NOT NULL COMMENT 'Human-readable label',
    PROPERTIES      VARIANT               COMMENT 'Additional attributes as JSON',
    DEGREE_IN       NUMBER(38,0) DEFAULT 0,
    DEGREE_OUT      NUMBER(38,0) DEFAULT 0,
    DEGREE_TOTAL    NUMBER(38,0) DEFAULT 0,
    COMPONENT_ID    NUMBER(38,0)          COMMENT 'WCC component assignment',
    PAGERANK        FLOAT        DEFAULT 0,
    HUB_SCORE       FLOAT        DEFAULT 0,
    AUTHORITY_SCORE FLOAT        DEFAULT 0,
    BETWEENNESS     FLOAT        DEFAULT 0,
    PRIMARY KEY (NODE_ID)
) COMMENT = 'Knowledge graph nodes — one row per canonical entity';

CREATE OR REPLACE TABLE SCS.KG.KG_EDGES (
    EDGE_ID       NUMBER(38,0) NOT NULL,
    FROM_NODE_ID  NUMBER(38,0) NOT NULL,
    TO_NODE_ID    NUMBER(38,0) NOT NULL,
    EDGE_TYPE     VARCHAR(40)  NOT NULL,
    WEIGHT        FLOAT        DEFAULT 1,
    PROPERTIES    VARIANT,
    BETWEENNESS   FLOAT        DEFAULT 0,
    PRIMARY KEY (EDGE_ID)
) COMMENT = 'Knowledge graph edges';

-- 4b. Data import via internal stage
-- On the SOURCE instance, export data:
--
--   CREATE OR REPLACE STAGE SCS.KG.EXPORT_STAGE;
--   COPY INTO @SCS.KG.EXPORT_STAGE/kg_nodes
--     FROM SCS.KG.KG_NODES
--     FILE_FORMAT = (TYPE=PARQUET)
--     OVERWRITE = TRUE;
--   COPY INTO @SCS.KG.EXPORT_STAGE/kg_edges
--     FROM SCS.KG.KG_EDGES
--     FILE_FORMAT = (TYPE=PARQUET)
--     OVERWRITE = TRUE;
--   GET @SCS.KG.EXPORT_STAGE/kg_nodes file:///tmp/kg_export/;
--   GET @SCS.KG.EXPORT_STAGE/kg_edges file:///tmp/kg_export/;
--
-- On the TARGET instance, import:
--
--   CREATE OR REPLACE STAGE SCS.KG.IMPORT_STAGE;
--   PUT file:///tmp/kg_export/kg_nodes* @SCS.KG.IMPORT_STAGE/kg_nodes AUTO_COMPRESS=FALSE;
--   PUT file:///tmp/kg_export/kg_edges* @SCS.KG.IMPORT_STAGE/kg_edges AUTO_COMPRESS=FALSE;
--
--   COPY INTO SCS.KG.KG_NODES
--     FROM @SCS.KG.IMPORT_STAGE/kg_nodes
--     FILE_FORMAT = (TYPE=PARQUET)
--     MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
--
--   COPY INTO SCS.KG.KG_EDGES
--     FROM @SCS.KG.IMPORT_STAGE/kg_edges
--     FILE_FORMAT = (TYPE=PARQUET)
--     MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;


-- =============================================================================
-- PART 5: KG VIEWS
-- =============================================================================
USE ROLE SUPPLYCHAIN;

-- 5a. Business metrics view (joins KG nodes to INVENTORY business tables)
CREATE OR REPLACE VIEW SCS.KG.KG_NODE_BUSINESS_METRICS
  COMMENT = 'Business-derived metrics per KG node — spend, quality, lead time, revenue'
AS
WITH supplier_spend AS (
    SELECT ph.SUPPLIER_ID,
           COUNT(DISTINCT ph.PO_ID) AS PO_COUNT,
           SUM(pl.QUANTITY * pl.UNIT_PRICE) AS TOTAL_SPEND
    FROM SCS.INVENTORY.PO_HEADER ph
    JOIN SCS.INVENTORY.PO_LINE pl ON ph.PO_ID = pl.PO_ID
    GROUP BY ph.SUPPLIER_ID
),
supplier_lead_time AS (
    SELECT ph.SUPPLIER_ID,
           ROUND(AVG(gr.DAYS_VARIANCE), 1) AS AVG_LEAD_TIME_VARIANCE,
           COUNT(*) AS RECEIPT_COUNT
    FROM SCS.INVENTORY.GOODS_RECEIPT gr
    JOIN SCS.INVENTORY.PO_LINE pl ON gr.PO_LINE_ID = pl.PO_LINE_ID
    JOIN SCS.INVENTORY.PO_HEADER ph ON pl.PO_ID = ph.PO_ID
    GROUP BY ph.SUPPLIER_ID
),
supplier_quality AS (
    SELECT SUPPLIER_ID,
           ROUND(AVG(PPM), 1) AS AVG_PPM,
           COUNT(*) AS INSPECTION_COUNT,
           ROUND(SUM(CASE WHEN RESULT = 'FAIL' THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0) * 100, 1) AS FAIL_RATE_PCT
    FROM SCS.INVENTORY.QUALITY_INSPECTION
    GROUP BY SUPPLIER_ID
),
supplier_ncr AS (
    SELECT SUPPLIER_ID,
           COUNT(*) AS NCR_COUNT,
           SUM(CASE WHEN SEVERITY = 'CRITICAL' THEN 1 ELSE 0 END) AS CRITICAL_NCR_COUNT
    FROM SCS.INVENTORY.NONCONFORMANCE_REPORT
    GROUP BY SUPPLIER_ID
),
part_quality AS (
    SELECT PART_ID,
           ROUND(AVG(PPM), 1) AS AVG_PPM,
           COUNT(*) AS INSPECTION_COUNT,
           ROUND(SUM(CASE WHEN RESULT = 'FAIL' THEN 1 ELSE 0 END)
                 / NULLIF(COUNT(*), 0) * 100, 1) AS FAIL_RATE_PCT
    FROM SCS.INVENTORY.QUALITY_INSPECTION
    GROUP BY PART_ID
),
part_ncr AS (
    SELECT PART_ID, COUNT(*) AS NCR_COUNT
    FROM SCS.INVENTORY.NONCONFORMANCE_REPORT
    GROUP BY PART_ID
),
product_revenue AS (
    SELECT sol.PRODUCT_ID,
           SUM(sol.QUANTITY * sol.UNIT_PRICE) AS TOTAL_REVENUE,
           COUNT(DISTINCT sol.ORDER_ID) AS ORDER_COUNT
    FROM SCS.INVENTORY.SALES_ORDER_LINE sol
    GROUP BY sol.PRODUCT_ID
),
customer_revenue AS (
    SELECT soh.CUSTOMER_ID,
           SUM(sol.QUANTITY * sol.UNIT_PRICE) AS TOTAL_REVENUE,
           COUNT(DISTINCT soh.ORDER_ID) AS ORDER_COUNT
    FROM SCS.INVENTORY.SALES_ORDER_HEADER soh
    JOIN SCS.INVENTORY.SALES_ORDER_LINE sol ON soh.ORDER_ID = sol.ORDER_ID
    GROUP BY soh.CUSTOMER_ID
),
plant_ncr AS (
    SELECT PLANT_ID,
           COUNT(*) AS NCR_COUNT,
           SUM(CASE WHEN SEVERITY = 'CRITICAL' THEN 1 ELSE 0 END) AS CRITICAL_NCR_COUNT
    FROM SCS.INVENTORY.NONCONFORMANCE_REPORT
    GROUP BY PLANT_ID
)
SELECT
    n.NODE_ID,
    ss.TOTAL_SPEND,
    ss.PO_COUNT,
    slt.AVG_LEAD_TIME_VARIANCE,
    slt.RECEIPT_COUNT,
    COALESCE(sq.AVG_PPM, pq.AVG_PPM) AS AVG_PPM,
    COALESCE(sq.INSPECTION_COUNT, pq.INSPECTION_COUNT) AS INSPECTION_COUNT,
    COALESCE(sq.FAIL_RATE_PCT, pq.FAIL_RATE_PCT) AS FAIL_RATE_PCT,
    COALESCE(sncr.NCR_COUNT, pncr.NCR_COUNT, plncr.NCR_COUNT) AS NCR_COUNT,
    COALESCE(sncr.CRITICAL_NCR_COUNT, plncr.CRITICAL_NCR_COUNT) AS CRITICAL_NCR_COUNT,
    ds.RELIABILITY_RATING,
    COALESCE(pr.TOTAL_REVENUE, cr.TOTAL_REVENUE) AS TOTAL_REVENUE,
    COALESCE(pr.ORDER_COUNT, cr.ORDER_COUNT) AS ORDER_COUNT
FROM SCS.KG.KG_NODES n
LEFT JOIN supplier_spend     ss    ON n.NODE_TYPE = 'SUPPLIER' AND n.SOURCE_ID = ss.SUPPLIER_ID
LEFT JOIN supplier_lead_time slt   ON n.NODE_TYPE = 'SUPPLIER' AND n.SOURCE_ID = slt.SUPPLIER_ID
LEFT JOIN supplier_quality   sq    ON n.NODE_TYPE = 'SUPPLIER' AND n.SOURCE_ID = sq.SUPPLIER_ID
LEFT JOIN supplier_ncr       sncr  ON n.NODE_TYPE = 'SUPPLIER' AND n.SOURCE_ID = sncr.SUPPLIER_ID
LEFT JOIN SCS.INVENTORY.DIM_SUPPLIER ds ON n.NODE_TYPE = 'SUPPLIER' AND n.SOURCE_ID = ds.SUPPLIER_ID
LEFT JOIN part_quality       pq    ON n.NODE_TYPE = 'PART'     AND n.SOURCE_ID = pq.PART_ID
LEFT JOIN part_ncr           pncr  ON n.NODE_TYPE = 'PART'     AND n.SOURCE_ID = pncr.PART_ID
LEFT JOIN product_revenue    pr    ON n.NODE_TYPE = 'PRODUCT'  AND n.SOURCE_ID = pr.PRODUCT_ID
LEFT JOIN customer_revenue   cr    ON n.NODE_TYPE = 'CUSTOMER' AND n.SOURCE_ID = cr.CUSTOMER_ID
LEFT JOIN plant_ncr          plncr ON n.NODE_TYPE = 'PLANT'    AND n.SOURCE_ID = plncr.PLANT_ID;

-- 5b. Node importance view
CREATE OR REPLACE VIEW SCS.KG.VW_NODE_IMPORTANCE AS
SELECT
    NODE_ID, NODE_TYPE, LABEL,
    DEGREE_TOTAL,
    ROUND(PAGERANK, 8) AS PAGERANK,
    ROUND(HUB_SCORE, 8) AS HUB_SCORE,
    ROUND(AUTHORITY_SCORE, 8) AS AUTHORITY_SCORE,
    ROUND(BETWEENNESS, 8) AS BETWEENNESS,
    COMPONENT_ID,
    ROUND((
        PERCENT_RANK() OVER (ORDER BY DEGREE_TOTAL) +
        PERCENT_RANK() OVER (ORDER BY PAGERANK) +
        PERCENT_RANK() OVER (ORDER BY HUB_SCORE) +
        PERCENT_RANK() OVER (ORDER BY AUTHORITY_SCORE) +
        PERCENT_RANK() OVER (ORDER BY BETWEENNESS)
    ) / 5.0, 6) AS COMPOSITE_IMPORTANCE
FROM SCS.KG.KG_NODES;

-- 5c. Community summary
CREATE OR REPLACE VIEW SCS.KG.VW_COMMUNITY_SUMMARY AS
SELECT
    COMPONENT_ID,
    COUNT(*) AS COMPONENT_SIZE,
    LISTAGG(DISTINCT NODE_TYPE, ', ') WITHIN GROUP (ORDER BY NODE_TYPE) AS NODE_TYPES,
    MAX(PAGERANK) AS MAX_PAGERANK,
    MAX(DEGREE_TOTAL) AS MAX_DEGREE,
    ROUND(AVG(DEGREE_TOTAL), 1) AS AVG_DEGREE,
    MAX_BY(LABEL, PAGERANK) AS TOP_NODE_BY_PR,
    MAX_BY(LABEL, DEGREE_TOTAL) AS TOP_NODE_BY_DEGREE
FROM SCS.KG.KG_NODES
GROUP BY COMPONENT_ID;

-- 5d. Single point of failure
CREATE OR REPLACE VIEW SCS.KG.VW_SINGLE_POINT_OF_FAILURE AS
SELECT
    N.NODE_ID, N.NODE_TYPE, N.LABEL,
    N.DEGREE_TOTAL, N.PAGERANK, N.BETWEENNESS,
    COUNT(DISTINCT NEIGHBOR.COMPONENT_ID) AS NEIGHBOR_COMPONENT_COUNT,
    ROUND(N.BETWEENNESS * N.DEGREE_TOTAL, 4) AS CRITICALITY_SCORE
FROM SCS.KG.KG_NODES N
JOIN SCS.KG.KG_EDGES E ON E.FROM_NODE_ID = N.NODE_ID OR E.TO_NODE_ID = N.NODE_ID
JOIN SCS.KG.KG_NODES NEIGHBOR ON NEIGHBOR.NODE_ID =
    CASE WHEN E.FROM_NODE_ID = N.NODE_ID THEN E.TO_NODE_ID ELSE E.FROM_NODE_ID END
GROUP BY N.NODE_ID, N.NODE_TYPE, N.LABEL, N.DEGREE_TOTAL, N.PAGERANK, N.BETWEENNESS
HAVING CRITICALITY_SCORE > 0
ORDER BY CRITICALITY_SCORE DESC;

-- 5e. BOM explosion (recursive)
CREATE OR REPLACE VIEW SCS.KG.VW_BOM_EXPLOSION AS
WITH RECURSIVE BOM_TREE AS (
    SELECT
        N.NODE_ID AS ROOT_NODE_ID, N.LABEL AS PRODUCT_LABEL,
        N.NODE_ID AS CURRENT_NODE_ID, N.LABEL AS CURRENT_LABEL,
        N.NODE_TYPE AS CURRENT_TYPE, 0 AS HOP, N.LABEL AS PATH
    FROM SCS.KG.KG_NODES N WHERE N.NODE_TYPE = 'PRODUCT'
    UNION ALL
    SELECT
        BT.ROOT_NODE_ID, BT.PRODUCT_LABEL,
        E.FROM_NODE_ID, N2.LABEL, N2.NODE_TYPE,
        BT.HOP + 1, BT.PATH || ' > ' || N2.LABEL
    FROM BOM_TREE BT
    JOIN SCS.KG.KG_EDGES E ON E.TO_NODE_ID = BT.CURRENT_NODE_ID AND E.EDGE_TYPE = 'COMPONENT_OF'
    JOIN SCS.KG.KG_NODES N2 ON N2.NODE_ID = E.FROM_NODE_ID
    WHERE BT.HOP < 5
)
SELECT * FROM BOM_TREE WHERE HOP > 0;

-- 5f. Disruption exposure (recursive)
CREATE OR REPLACE VIEW SCS.KG.VW_DISRUPTION_EXPOSURE AS
WITH RECURSIVE EXPOSURE_PATH AS (
    SELECT
        N.NODE_ID AS ORIGIN_NODE_ID, N.LABEL AS ORIGIN_LABEL, N.NODE_TYPE AS ORIGIN_TYPE,
        N.NODE_ID AS CURRENT_NODE_ID, N.LABEL AS CURRENT_LABEL, N.NODE_TYPE AS CURRENT_TYPE,
        0 AS HOP, N.LABEL AS PATH_STR, N.NODE_ID::VARCHAR AS PATH_IDS
    FROM SCS.KG.KG_NODES N WHERE N.NODE_TYPE = 'SUPPLIER_SITE'
    UNION ALL
    SELECT
        EP.ORIGIN_NODE_ID, EP.ORIGIN_LABEL, EP.ORIGIN_TYPE,
        E.TO_NODE_ID, N2.LABEL, N2.NODE_TYPE,
        EP.HOP + 1, EP.PATH_STR || ' -> ' || N2.LABEL,
        EP.PATH_IDS || ',' || E.TO_NODE_ID::VARCHAR
    FROM EXPOSURE_PATH EP
    JOIN SCS.KG.KG_EDGES E ON E.FROM_NODE_ID = EP.CURRENT_NODE_ID
        AND E.EDGE_TYPE IN ('APPROVED_SOURCE','COMPONENT_OF','SUPPLIES_TO','SHIPS_TO')
    JOIN SCS.KG.KG_NODES N2 ON N2.NODE_ID = E.TO_NODE_ID
    WHERE EP.HOP < 4 AND NOT CONTAINS(EP.PATH_IDS, E.TO_NODE_ID::VARCHAR)
)
SELECT ORIGIN_NODE_ID, ORIGIN_LABEL, ORIGIN_TYPE,
       CURRENT_NODE_ID AS AFFECTED_NODE_ID, CURRENT_LABEL AS AFFECTED_LABEL,
       CURRENT_TYPE AS AFFECTED_TYPE, HOP, PATH_STR
FROM EXPOSURE_PATH WHERE HOP > 0;


-- =============================================================================
-- PART 6: DOCUMENT CORPUS (10 rows — inline INSERT)
-- =============================================================================
USE ROLE SUPPLYCHAIN;

CREATE OR REPLACE TABLE SCS.SEMANTIC.DOCUMENT_CORPUS (
    DOC_ID        NUMBER(38,0)  NOT NULL PRIMARY KEY,
    DOC_TYPE      VARCHAR(30)   NOT NULL,
    TITLE         VARCHAR(300)  NOT NULL,
    DOC_TEXT      VARCHAR(5000) NOT NULL,
    SUPPLIER_NAME VARCHAR(200),
    PART_NAME     VARCHAR(200),
    PLANT_NAME    VARCHAR(100),
    EVENT_DATE    DATE,
    SEVERITY      VARCHAR(20),
    IS_SYNTHETIC  BOOLEAN       DEFAULT TRUE
) COMMENT = 'Fabricated document corpus for Cortex Search — contracts, NCRs, scorecards, alerts';

INSERT INTO SCS.SEMANTIC.DOCUMENT_CORPUS VALUES
(1,'CONTRACT','NEXORA Master Supply Agreement - Force Majeure Clause','Section 12.1 Force Majeure: Neither party shall be liable for delays caused by acts of God, war, government regulation, customs delays, or port closures. The affected party must provide written notice within 5 business days. If force majeure extends beyond 90 days, either party may terminate without penalty. NEXORA SEMICONDUCTORS Penang site is subject to extended customs inspection protocols under clause 12.1.3.','NEXORA SEMICONDUCTORS',NULL,'Asterion Guadalajara','2024-06-15','MAJOR',TRUE),
(2,'CONTRACT','NEXORA Liability Cap and LTB Rights','Section 8.2 Liability: NEXORA total liability under this agreement shall not exceed 200% of the annual purchase volume. Section 15.3 Last Time Buy: Upon EOL notification, buyer has 180 days to place a final order. NEXORA must maintain 12 months of safety stock for allocated parts during the transition period.','NEXORA SEMICONDUCTORS',NULL,NULL,'2024-06-15',NULL,TRUE),
(3,'NCR','NCR-2026-0312 Cracked Ceramic Substrates','Non-conformance report for lot SZ-20260301-A from NEXORA Penang site. 14 of 200 ceramic substrates showed micro-cracks during incoming inspection. Root cause: excessive shock (4.2G peak) during ocean transit on Shenzhen-Guadalajara lane. Disposition: SCRAP. Corrective action: require shock-absorbing packaging and real-time IoT monitoring for all NEXORA ocean shipments on this lane.','NEXORA SEMICONDUCTORS','Ceramic Substrates','Asterion Guadalajara','2026-03-12','CRITICAL',TRUE),
(4,'NCR','NCR-2026-0415 Temperature Excursion','Non-conformance report for NEXORA memory IC shipment via Shenzhen-Guadalajara ocean lane. Container temperature exceeded 45C for 18 hours during customs hold at Manzanillo. 8% of ICs showed parametric drift beyond specification. Root cause: customs delay compounded by inadequate container cooling. Disposition: REWORK (re-test and re-screen).','NEXORA SEMICONDUCTORS','Memory ICs','Asterion Guadalajara','2026-04-15','MAJOR',TRUE),
(5,'SCORECARD','NEXORA Q2 2026 Supplier Scorecard','NEXORA SEMICONDUCTORS quarterly performance review. OTD: 62% (target 90%, down from 78% in Q1). Quality PPM: 4,200 (target <1,000). Responsiveness: BELOW EXPECTATIONS — average RFQ response time 12 days vs 5-day target. Cost competitiveness: MEETS EXPECTATIONS. Overall rating: CRITICAL — requires immediate corrective action plan. Penang site is primary contributor to missed deliveries.','NEXORA SEMICONDUCTORS',NULL,NULL,'2026-06-30','CRITICAL',TRUE),
(6,'ALERT','Customs Delay Alert - Shenzhen-Guadalajara Lane','EXCEPTION ALERT SCN_2026_SHENZHEN_GUADALAJARA_CUSTOMS: Starting March 2026, new customs inspection protocols at Manzanillo port have increased clearance times from 2 days to 8-14 days for electronics shipments from China. Impact: 23 shipments delayed, 4 containers held for extended inspection. Affected suppliers: NEXORA, BLUEFORGE, and 3 others using this lane.','NEXORA SEMICONDUCTORS',NULL,'Asterion Guadalajara','2026-03-01','CRITICAL',TRUE),
(7,'SCORECARD','BLUEFORGE Q2 2026 Supplier Scorecard','BLUEFORGE COMPONENTS quarterly review. OTD: 71% (target 90%). Quality: 2,800 PPM (target <1,000). Multiple lots with solder joint defects traced to process change at Shenzhen facility. Delivery delays primarily on ocean shipments through Manzanillo customs. Corrective action plan submitted but not yet validated.','BLUEFORGE COMPONENTS',NULL,NULL,'2026-06-30','MAJOR',TRUE),
(8,'ECO','ECO-2026-0089 Alternate Source Qualification','Engineering Change Order to qualify STELLAR TECHNOLOGIES as alternate source for MCU-P00012 currently single-sourced from NEXORA Penang. Rationale: supply risk mitigation due to customs disruption on Shenzhen-Guadalajara lane. Estimated qualification timeline: 16 weeks. Affected products: PROD-0001 through PROD-0025.','NEXORA SEMICONDUCTORS','MCU-P00012',NULL,'2026-05-10',NULL,TRUE),
(9,'ALERT','Single Source Risk Alert - Semiconductor Parts','RISK ALERT: 47 semiconductor parts are single-sourced from NEXORA or BLUEFORGE. Combined annual spend at risk: $12.4M. Highest impact parts: MCU-P00012 (used in 18 products), DRAM-P00045 (used in 12 products). Recommendation: immediate qualification of alternate sources per ECO-2026-0089.',NULL,NULL,NULL,'2026-04-01','MAJOR',TRUE),
(10,'CONTRACT','PENTAWAVE Materials Supply Agreement','PENTAWAVE MATERIALS contract CTR-00015. Section 5.1: Price escalation capped at 3% annually. Section 9.2: Quality guarantee of <500 PPM. Section 11.1: Delivery tolerance window of -3 to +2 days from confirmed date. Section 14.1: Substitution rights — buyer may approve equivalent materials if lead time exceeds 60 days.','PENTAWAVE MATERIALS',NULL,NULL,'2025-01-15',NULL,TRUE);


-- =============================================================================
-- PART 7: SEMANTIC VIEW
-- =============================================================================
USE ROLE SUPPLYCHAIN;

CREATE OR REPLACE SEMANTIC VIEW SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG
  TABLES (
    NODES AS SCS.KG.KG_NODES
      PRIMARY KEY (NODE_ID)
      WITH SYNONYMS = ('entities','graph nodes','supply chain entities')
      COMMENT = 'Knowledge graph nodes with graph analytics',
    EDGES AS SCS.KG.KG_EDGES
      PRIMARY KEY (EDGE_ID)
      WITH SYNONYMS = ('relationships','graph edges','links','connections')
      COMMENT = 'Knowledge graph edges'
  )
  RELATIONSHIPS (
    EDGE_FROM_NODE AS EDGES(FROM_NODE_ID) REFERENCES NODES(NODE_ID),
    EDGE_TO_NODE   AS EDGES(TO_NODE_ID)   REFERENCES NODES(NODE_ID)
  )
  FACTS (
    NODES.DEGREE_IN_VAL      AS NODES.DEGREE_IN        COMMENT = 'Incoming edge count',
    NODES.DEGREE_OUT_VAL     AS NODES.DEGREE_OUT       COMMENT = 'Outgoing edge count',
    NODES.DEGREE_TOTAL_VAL   AS NODES.DEGREE_TOTAL     COMMENT = 'Total connections (in + out)',
    NODES.PAGERANK_VAL       AS NODES.PAGERANK         COMMENT = 'PageRank importance score',
    NODES.HUB_SCORE_VAL      AS NODES.HUB_SCORE        COMMENT = 'HITS hub score',
    NODES.AUTHORITY_SCORE_VAL AS NODES.AUTHORITY_SCORE  COMMENT = 'HITS authority score',
    NODES.BETWEENNESS_VAL    AS NODES.BETWEENNESS      COMMENT = 'Betweenness centrality',
    EDGES.EDGE_WEIGHT        AS EDGES.WEIGHT           COMMENT = 'Edge weight (transaction count)',
    EDGES.EDGE_BETWEENNESS   AS EDGES.BETWEENNESS      COMMENT = 'Edge betweenness score'
  )
  DIMENSIONS (
    NODES.NODE_TYPE   AS NODES.NODE_TYPE
      WITH SYNONYMS = ('entity type','class','category')
      COMMENT = 'Entity type: SUPPLIER, PART, PRODUCT, PLANT, WAREHOUSE, CUSTOMER, CARRIER, COMMODITY, PORT, COUNTRY, LANE, SUPPLIER_SITE',
    NODES.ENTITY_NAME AS NODES.LABEL
      WITH SYNONYMS = ('name','node name','title','entity name')
      COMMENT = 'Human-readable name of the entity',
    NODES.COMPONENT   AS NODES.COMPONENT_ID
      WITH SYNONYMS = ('community','cluster','WCC component','group')
      COMMENT = 'Weakly Connected Component ID',
    EDGES.RELATIONSHIP_TYPE AS EDGES.EDGE_TYPE
      WITH SYNONYMS = ('edge type','link type','connection type')
      COMMENT = 'Relationship type: HAS_SITE, APPROVED_SOURCE, COMPONENT_OF, SUPPLIES_TO, SHIPS_TO, etc.'
  )
  METRICS (
    NODES.TOTAL_NODES    AS COUNT(DISTINCT NODES.NODE_ID) WITH SYNONYMS = ('node count','entity count') COMMENT = 'Total nodes',
    NODES.AVG_DEGREE     AS AVG(NODES.DEGREE_TOTAL_VAL)   WITH SYNONYMS = ('average connectivity')     COMMENT = 'Average degree',
    NODES.MAX_PAGERANK   AS MAX(NODES.PAGERANK_VAL)        WITH SYNONYMS = ('top pagerank')             COMMENT = 'Highest PageRank',
    NODES.COMPONENT_COUNT AS COUNT(DISTINCT NODES.COMPONENT) WITH SYNONYMS = ('community count')        COMMENT = 'Number of WCC components',
    EDGES.TOTAL_EDGES    AS COUNT(DISTINCT EDGES.EDGE_ID)  WITH SYNONYMS = ('edge count','link count')  COMMENT = 'Total edges'
  )
  COMMENT = 'Supply chain knowledge graph with PageRank, WCC, HITS, betweenness centrality'
  AI_SQL_GENERATION
    'Use PAGERANK for importance ranking. Use DEGREE_TOTAL for connectivity. Use BETWEENNESS for bottlenecks. '
    'Use COMPONENT_ID for communities. Use HUB_SCORE for connector nodes, AUTHORITY_SCORE for destination nodes. '
    'For supplier-plant links use EDGE_TYPE=SUPPLIES_TO. For BOM use EDGE_TYPE=COMPONENT_OF. '
    'NODE_TYPE values: SUPPLIER, SUPPLIER_SITE, PART, PRODUCT, PLANT, WAREHOUSE, CUSTOMER, CARRIER, COMMODITY, PORT, COUNTRY, LANE. '
    'All data is synthetic.'
  AI_VERIFIED_QUERIES (
    TOP_CRITICAL_SUPPLIERS AS (
      QUESTION 'Which are the most critical suppliers in the supply chain?'
      SQL 'SELECT NODE_ID, LABEL AS SUPPLIER_NAME, PAGERANK, DEGREE_TOTAL, HUB_SCORE, BETWEENNESS FROM SCS.KG.KG_NODES WHERE NODE_TYPE = ''SUPPLIER'' ORDER BY PAGERANK DESC LIMIT 10'
    ),
    GRAPH_SUMMARY AS (
      QUESTION 'Give me a summary of the knowledge graph'
      SQL 'SELECT COUNT(DISTINCT NODE_ID) AS TOTAL_NODES, (SELECT COUNT(*) FROM SCS.KG.KG_EDGES) AS TOTAL_EDGES, COUNT(DISTINCT COMPONENT_ID) AS COMPONENTS, ROUND(AVG(DEGREE_TOTAL),1) AS AVG_DEGREE FROM SCS.KG.KG_NODES'
    )
  );


-- =============================================================================
-- PART 8: CORTEX SEARCH SERVICE
-- =============================================================================
USE ROLE SUPPLYCHAIN;

CREATE OR REPLACE CORTEX SEARCH SERVICE SCS.SEMANTIC.SCM_DOCUMENT_SEARCH
  ON DOC_TEXT
  ATTRIBUTES DOC_TYPE, SUPPLIER_NAME, SEVERITY
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 day'
AS (
    SELECT DOC_ID, DOC_TYPE, TITLE, DOC_TEXT, SUPPLIER_NAME, PART_NAME,
           PLANT_NAME, EVENT_DATE, SEVERITY
    FROM SCS.SEMANTIC.DOCUMENT_CORPUS
);


-- =============================================================================
-- PART 9: CORTEX AGENTS
-- =============================================================================
USE ROLE SUPPLYCHAIN;

-- 9a. SCM_KG_CHATBOT (minimal agent used by Streamlit app)
CREATE OR REPLACE AGENT SCS.SEMANTIC.SCM_KG_CHATBOT
  COMMENT = 'Supply chain knowledge graph chatbot powered by Claude Opus 5';

ALTER AGENT SCS.SEMANTIC.SCM_KG_CHATBOT ADD LIVE VERSION FROM LAST;

-- 9b. SUPPLY_CHAIN_KG_AGENT (full-featured agent with sql_exec + charting)
CREATE OR REPLACE AGENT SCS.SEMANTIC.SUPPLY_CHAIN_KG_AGENT
  COMMENT = 'Supply-chain KG agent: Cortex Analyst over SV_SUPPLY_CHAIN_KG, Cortex Search over SCM_DOCUMENT_SEARCH, sql_exec on COMPUTE_WH'
  PROFILE = '{"display_name": "Supply Chain KG"}'
  FROM SPECIFICATION $$
{
  "models": {"orchestration": "auto"},
  "instructions": {
    "response": "You are a supply-chain analyst assistant answering questions about the Asterion Devices supply chain. Answer with findings only — no narration of your own steps. Present rankings, breakdowns and trends as a markdown table with a header row, a separator row, and no blank lines between rows. Express monetary figures in USD. Refer to time periods by calendar date, never by week number.",
    "orchestration": "Use the supply_chain_kg tool for anything about entities and their relationships — suppliers, supplier sites, parts, products, plants, warehouses, customers, lanes, ports, carriers and countries — including graph analytics such as importance (PAGERANK), connectivity (DEGREE_TOTAL), bottlenecks (BETWEENNESS) and communities (COMPONENT_ID). Use the supply_chain_docs tool for questions about contracts, non-conformance reports, supplier scorecards and risk alerts. Always execute the SQL you generate with sql_exec and answer from the rows it returns — never present un-executed SQL as the answer.",
    "sample_questions": [
      {"question": "Which are the most critical suppliers in the supply chain?"},
      {"question": "Which supplier sites are single points of failure?"},
      {"question": "Which parts have the most alternate approved sources?"},
      {"question": "Give me a summary of the knowledge graph"}
    ]
  },
  "tools": [
    {"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "supply_chain_kg", "description": "Supply-chain knowledge graph: nodes (suppliers, supplier sites, parts, products, plants, warehouses, customers, lanes, ports, carriers, countries, commodities) and the edges between them, with precomputed PageRank, degree, HITS hub/authority, betweenness and connected components."}},
    {"tool_spec": {"type": "cortex_search", "name": "supply_chain_docs", "description": "Unstructured supply-chain documents: supplier contracts, non-conformance reports, supplier scorecards and risk alerts."}},
    {"tool_spec": {"type": "sql_exec", "name": "sql_exec", "description": "Executes the generated SQL on the warehouse."}},
    {"tool_spec": {"type": "data_to_chart", "name": "data_to_chart", "description": "Generates visualizations from returned data."}}
  ],
  "tool_resources": {
    "supply_chain_kg": {
      "semantic_view": "SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG",
      "execution_environment": {"type": "warehouse", "warehouse": "COMPUTE_WH", "query_timeout": 120}
    },
    "supply_chain_docs": {
      "search_service": "SCS.SEMANTIC.SCM_DOCUMENT_SEARCH",
      "max_results": "5"
    }
  }
}
$$;

ALTER AGENT SCS.SEMANTIC.SUPPLY_CHAIN_KG_AGENT ADD LIVE VERSION FROM LAST;
ALTER AGENT SCS.SEMANTIC.SUPPLY_CHAIN_KG_AGENT COMMIT
  COMMENT = 'Initial production deployment';


-- =============================================================================
-- PART 10: AI & CROSS-ROLE GRANTS
-- =============================================================================
USE ROLE ACCOUNTADMIN;

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SUPPLYCHAIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE GE_MCP_ROLE;

-- Grant GE_MCP_ROLE access through SUPPLYCHAIN inheritance
GRANT ROLE SUPPLYCHAIN TO ROLE GE_MCP_ROLE;


-- =============================================================================
-- VALIDATION QUERIES (run after full deployment)
-- =============================================================================
USE ROLE SUPPLYCHAIN;
USE WAREHOUSE COMPUTE_WH;

-- Verify table counts
SELECT 'KG_NODES' AS OBJ, COUNT(*) AS ROWS FROM SCS.KG.KG_NODES
UNION ALL SELECT 'KG_EDGES', COUNT(*) FROM SCS.KG.KG_EDGES
UNION ALL SELECT 'DOCUMENT_CORPUS', COUNT(*) FROM SCS.SEMANTIC.DOCUMENT_CORPUS;

-- Verify semantic view
SHOW SEMANTIC VIEWS LIKE 'SV_SUPPLY_CHAIN_KG' IN SCHEMA SCS.SEMANTIC;

-- Verify Cortex Search
SHOW CORTEX SEARCH SERVICES LIKE 'SCM_DOCUMENT_SEARCH' IN SCHEMA SCS.SEMANTIC;

-- Verify agents
SHOW AGENTS IN SCHEMA SCS.SEMANTIC;

-- Test the agent
SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
  'SCS.SEMANTIC.SUPPLY_CHAIN_KG_AGENT',
  $${"messages": [{"role": "user", "content": [{"type": "text", "text": "How many nodes are in the graph?"}]}]}$$
);
