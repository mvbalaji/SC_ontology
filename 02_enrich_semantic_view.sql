-- =============================================================
-- Step 1: Create business metrics view per KG node
-- =============================================================
USE ROLE SUPPLYCHAIN;
USE WAREHOUSE COMPUTE_WH;

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
    COALESCE(sq.AVG_PPM, pq.AVG_PPM)                                    AS AVG_PPM,
    COALESCE(sq.INSPECTION_COUNT, pq.INSPECTION_COUNT)                   AS INSPECTION_COUNT,
    COALESCE(sq.FAIL_RATE_PCT, pq.FAIL_RATE_PCT)                        AS FAIL_RATE_PCT,
    COALESCE(sncr.NCR_COUNT, pncr.NCR_COUNT, plncr.NCR_COUNT)           AS NCR_COUNT,
    COALESCE(sncr.CRITICAL_NCR_COUNT, plncr.CRITICAL_NCR_COUNT)         AS CRITICAL_NCR_COUNT,
    ds.RELIABILITY_RATING,
    COALESCE(pr.TOTAL_REVENUE, cr.TOTAL_REVENUE)                         AS TOTAL_REVENUE,
    COALESCE(pr.ORDER_COUNT, cr.ORDER_COUNT)                             AS ORDER_COUNT
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

-- Quick validation
SELECT NODE_TYPE,
       COUNT(*) AS NODES,
       COUNT(TOTAL_SPEND) AS HAS_SPEND,
       COUNT(AVG_PPM) AS HAS_QUALITY,
       COUNT(TOTAL_REVENUE) AS HAS_REVENUE,
       COUNT(NCR_COUNT) AS HAS_NCR
FROM SCS.KG.KG_NODE_BUSINESS_METRICS bm
JOIN SCS.KG.KG_NODES n ON bm.NODE_ID = n.NODE_ID
GROUP BY NODE_TYPE
ORDER BY NODES DESC;


-- =============================================================
-- Step 2: Recreate the semantic view with business columns added
-- =============================================================
CREATE OR REPLACE SEMANTIC VIEW SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG
  TABLES (
    NODES AS SCS.KG.KG_NODES
      PRIMARY KEY (NODE_ID)
      WITH SYNONYMS = ('entities','graph nodes','supply chain entities')
      COMMENT = 'Knowledge graph nodes with graph analytics',

    EDGES AS SCS.KG.KG_EDGES
      PRIMARY KEY (EDGE_ID)
      WITH SYNONYMS = ('relationships','graph edges','links','connections')
      COMMENT = 'Knowledge graph edges',

    BIZ AS SCS.KG.KG_NODE_BUSINESS_METRICS
      PRIMARY KEY (NODE_ID)
      WITH SYNONYMS = ('business metrics','KPIs','operational metrics','performance')
      COMMENT = 'Business-derived metrics per node: spend, quality, lead time, revenue'
  )
  RELATIONSHIPS (
    EDGE_FROM_NODE AS EDGES(FROM_NODE_ID) REFERENCES NODES(NODE_ID),
    EDGE_TO_NODE   AS EDGES(TO_NODE_ID)   REFERENCES NODES(NODE_ID),
    BIZ_TO_NODE    AS BIZ(NODE_ID)        REFERENCES NODES(NODE_ID)
  )
  FACTS (
    -- Graph analytics
    NODES.DEGREE_IN_VAL     AS NODES.DEGREE_IN        COMMENT = 'Incoming edge count',
    NODES.DEGREE_OUT_VAL    AS NODES.DEGREE_OUT       COMMENT = 'Outgoing edge count',
    NODES.DEGREE_TOTAL_VAL  AS NODES.DEGREE_TOTAL     COMMENT = 'Total connections (in + out)',
    NODES.PAGERANK_VAL      AS NODES.PAGERANK         COMMENT = 'PageRank importance score',
    NODES.HUB_SCORE_VAL     AS NODES.HUB_SCORE        COMMENT = 'HITS hub score',
    NODES.AUTHORITY_SCORE_VAL AS NODES.AUTHORITY_SCORE COMMENT = 'HITS authority score',
    NODES.BETWEENNESS_VAL   AS NODES.BETWEENNESS      COMMENT = 'Betweenness centrality',
    EDGES.EDGE_WEIGHT       AS EDGES.WEIGHT           COMMENT = 'Edge weight (transaction count)',
    EDGES.EDGE_BETWEENNESS  AS EDGES.BETWEENNESS      COMMENT = 'Edge betweenness score',
    -- Business metrics
    BIZ.TOTAL_SPEND_VAL     AS BIZ.TOTAL_SPEND        COMMENT = 'Total PO spend (supplier nodes)',
    BIZ.PO_COUNT_VAL        AS BIZ.PO_COUNT           COMMENT = 'Number of purchase orders (supplier nodes)',
    BIZ.AVG_LEAD_TIME_VAR   AS BIZ.AVG_LEAD_TIME_VARIANCE COMMENT = 'Avg delivery days variance vs promise date (supplier nodes)',
    BIZ.AVG_PPM_VAL         AS BIZ.AVG_PPM            COMMENT = 'Average parts-per-million defect rate (supplier/part nodes)',
    BIZ.FAIL_RATE_VAL       AS BIZ.FAIL_RATE_PCT      COMMENT = 'Quality inspection failure rate % (supplier/part nodes)',
    BIZ.NCR_COUNT_VAL       AS BIZ.NCR_COUNT          COMMENT = 'Non-conformance report count (supplier/part/plant nodes)',
    BIZ.CRITICAL_NCR_VAL    AS BIZ.CRITICAL_NCR_COUNT COMMENT = 'Critical-severity NCR count (supplier/plant nodes)',
    BIZ.RELIABILITY_VAL     AS BIZ.RELIABILITY_RATING COMMENT = 'Supplier reliability rating 0-1 (supplier nodes)',
    BIZ.TOTAL_REVENUE_VAL   AS BIZ.TOTAL_REVENUE      COMMENT = 'Total sales revenue (product/customer nodes)',
    BIZ.ORDER_COUNT_VAL     AS BIZ.ORDER_COUNT        COMMENT = 'Number of sales orders (product/customer nodes)'
  )
  DIMENSIONS (
    NODES.NODE_TYPE  AS NODES.NODE_TYPE
      WITH SYNONYMS = ('entity type','class','category')
      COMMENT = 'Entity type: SUPPLIER, PART, PRODUCT, PLANT, WAREHOUSE, CUSTOMER, CARRIER, COMMODITY, PORT, COUNTRY, LANE, SUPPLIER_SITE',
    NODES.ENTITY_NAME AS NODES.LABEL
      WITH SYNONYMS = ('name','node name','title','entity name')
      COMMENT = 'Human-readable name of the entity',
    NODES.COMPONENT AS NODES.COMPONENT_ID
      WITH SYNONYMS = ('community','cluster','WCC component','group')
      COMMENT = 'Weakly Connected Component ID',
    EDGES.RELATIONSHIP_TYPE AS EDGES.EDGE_TYPE
      WITH SYNONYMS = ('edge type','link type','connection type')
      COMMENT = 'Relationship type: HAS_SITE, APPROVED_SOURCE, COMPONENT_OF, SUPPLIES_TO, SHIPS_TO, etc.'
  )
  METRICS (
    -- Graph metrics
    NODES.TOTAL_NODES    AS COUNT(DISTINCT NODES.NODE_ID) WITH SYNONYMS = ('node count','entity count') COMMENT = 'Total nodes',
    NODES.AVG_DEGREE     AS AVG(NODES.DEGREE_TOTAL_VAL)   WITH SYNONYMS = ('average connectivity')     COMMENT = 'Average degree',
    NODES.MAX_PAGERANK   AS MAX(NODES.PAGERANK_VAL)        WITH SYNONYMS = ('top pagerank')             COMMENT = 'Highest PageRank',
    NODES.COMPONENT_COUNT AS COUNT(DISTINCT NODES.COMPONENT) WITH SYNONYMS = ('community count')        COMMENT = 'Number of WCC components',
    EDGES.TOTAL_EDGES    AS COUNT(DISTINCT EDGES.EDGE_ID)  WITH SYNONYMS = ('edge count','link count')  COMMENT = 'Total edges',
    -- Business metrics
    BIZ.TOTAL_SPEND_SUM  AS SUM(BIZ.TOTAL_SPEND)  WITH SYNONYMS = ('total procurement spend','purchase spend') COMMENT = 'Sum of spend across nodes',
    BIZ.AVG_PPM_ALL      AS AVG(BIZ.AVG_PPM)      WITH SYNONYMS = ('average defect rate')                      COMMENT = 'Average PPM across nodes',
    BIZ.NCR_COUNT_SUM    AS SUM(BIZ.NCR_COUNT)     WITH SYNONYMS = ('total NCRs','nonconformance total')        COMMENT = 'Total NCR count',
    BIZ.TOTAL_REVENUE_SUM AS SUM(BIZ.TOTAL_REVENUE) WITH SYNONYMS = ('total revenue','sales total')             COMMENT = 'Sum of revenue across nodes'
  )
  COMMENT = 'Supply chain knowledge graph with PageRank, WCC, HITS, betweenness centrality, and business KPIs (spend, quality, lead time, revenue)'
  AI_SQL_GENERATION
    'Use PAGERANK for importance ranking. Use DEGREE_TOTAL for connectivity. Use BETWEENNESS for bottlenecks. '
    'Use COMPONENT_ID for communities. Use HUB_SCORE for connector nodes, AUTHORITY_SCORE for destination nodes. '
    'For supplier-plant links use EDGE_TYPE=SUPPLIES_TO. For BOM use EDGE_TYPE=COMPONENT_OF. '
    'NODE_TYPE values: SUPPLIER, SUPPLIER_SITE, PART, PRODUCT, PLANT, WAREHOUSE, CUSTOMER, CARRIER, COMMODITY, PORT, COUNTRY, LANE. '
    'TOTAL_SPEND, PO_COUNT, AVG_LEAD_TIME_VARIANCE, RELIABILITY_RATING apply only to SUPPLIER nodes. '
    'AVG_PPM and FAIL_RATE_PCT apply to SUPPLIER and PART nodes. '
    'TOTAL_REVENUE and ORDER_COUNT apply to PRODUCT and CUSTOMER nodes. '
    'NCR_COUNT applies to SUPPLIER, PART, and PLANT nodes. '
    'Always filter by NODE_TYPE when querying business metrics. All data is synthetic.'
  AI_VERIFIED_QUERIES (
    TOP_CRITICAL_SUPPLIERS AS (
      QUESTION 'Which are the most critical suppliers in the supply chain?'
      SQL 'SELECT n.NODE_ID, n.LABEL AS SUPPLIER_NAME, n.PAGERANK, n.DEGREE_TOTAL, n.HUB_SCORE, n.BETWEENNESS FROM SCS.KG.KG_NODES n WHERE n.NODE_TYPE = ''SUPPLIER'' ORDER BY n.PAGERANK DESC LIMIT 10'
    ),
    GRAPH_SUMMARY AS (
      QUESTION 'Give me a summary of the knowledge graph'
      SQL 'SELECT COUNT(DISTINCT NODE_ID) AS TOTAL_NODES, (SELECT COUNT(*) FROM SCS.KG.KG_EDGES) AS TOTAL_EDGES, COUNT(DISTINCT COMPONENT_ID) AS COMPONENTS, ROUND(AVG(DEGREE_TOTAL),1) AS AVG_DEGREE FROM SCS.KG.KG_NODES'
    ),
    TOP_SUPPLIERS_BY_SPEND AS (
      QUESTION 'Which suppliers have the highest spend?'
      SQL 'SELECT n.LABEL AS SUPPLIER_NAME, bm.TOTAL_SPEND, bm.PO_COUNT, n.PAGERANK FROM SCS.KG.KG_NODES n JOIN SCS.KG.KG_NODE_BUSINESS_METRICS bm ON n.NODE_ID = bm.NODE_ID WHERE n.NODE_TYPE = ''SUPPLIER'' AND bm.TOTAL_SPEND IS NOT NULL ORDER BY bm.TOTAL_SPEND DESC LIMIT 10'
    ),
    WORST_QUALITY_SUPPLIERS AS (
      QUESTION 'Which suppliers have the worst quality or highest defect rate?'
      SQL 'SELECT n.LABEL AS SUPPLIER_NAME, bm.AVG_PPM, bm.FAIL_RATE_PCT, bm.NCR_COUNT, bm.RELIABILITY_RATING FROM SCS.KG.KG_NODES n JOIN SCS.KG.KG_NODE_BUSINESS_METRICS bm ON n.NODE_ID = bm.NODE_ID WHERE n.NODE_TYPE = ''SUPPLIER'' AND bm.AVG_PPM IS NOT NULL ORDER BY bm.AVG_PPM DESC LIMIT 10'
    ),
    LATE_DELIVERY_SUPPLIERS AS (
      QUESTION 'Which suppliers have the worst delivery performance or lead time?'
      SQL 'SELECT n.LABEL AS SUPPLIER_NAME, bm.AVG_LEAD_TIME_VARIANCE, bm.RECEIPT_COUNT, bm.RELIABILITY_RATING FROM SCS.KG.KG_NODES n JOIN SCS.KG.KG_NODE_BUSINESS_METRICS bm ON n.NODE_ID = bm.NODE_ID WHERE n.NODE_TYPE = ''SUPPLIER'' AND bm.AVG_LEAD_TIME_VARIANCE IS NOT NULL ORDER BY bm.AVG_LEAD_TIME_VARIANCE DESC LIMIT 10'
    ),
    TOP_REVENUE_PRODUCTS AS (
      QUESTION 'Which products generate the most revenue?'
      SQL 'SELECT n.LABEL AS PRODUCT_NAME, bm.TOTAL_REVENUE, bm.ORDER_COUNT, n.PAGERANK FROM SCS.KG.KG_NODES n JOIN SCS.KG.KG_NODE_BUSINESS_METRICS bm ON n.NODE_ID = bm.NODE_ID WHERE n.NODE_TYPE = ''PRODUCT'' AND bm.TOTAL_REVENUE IS NOT NULL ORDER BY bm.TOTAL_REVENUE DESC LIMIT 10'
    )
  );


-- =============================================================
-- Step 3: Grant access
-- =============================================================
GRANT USAGE ON VIEW SCS.KG.KG_NODE_BUSINESS_METRICS TO ROLE GE_MCP_ROLE;
GRANT SELECT ON VIEW SCS.KG.KG_NODE_BUSINESS_METRICS TO ROLE GE_MCP_ROLE;


-- =============================================================
-- Step 4: Fix Streamlit chatbot (run as ACCOUNTADMIN)
-- =============================================================
-- Grant AI privileges
USE ROLE ACCOUNTADMIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE GE_MCP_ROLE;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SUPPLYCHAIN;
