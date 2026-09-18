-- Wire data tools onto the Cortex Data Agent behind this app.
--
-- Without this the agent has only its default file/pandas tools, cannot reach
-- SCS at all, and answers every business question by asking for a CSV.
--
-- Attaches:
--   supply_chain_kg    text-to-SQL over SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG
--                      (KG_NODES / KG_EDGES + PageRank, degree, HITS,
--                       betweenness, connected components)
--   supply_chain_docs  Cortex Search over SCS.SEMANTIC.SCM_DOCUMENT_SEARCH
--                      (contracts, NCRs, scorecards, risk alerts)
--   sql_exec           runs the generated SQL on COMPUTE_WH, so answers come
--                      from rows rather than from un-executed SQL
--   data_to_chart      lets the agent return a chart spec, which app.py
--                      already parses into the UI's chart panel
--
-- Run as SUPPLYCHAIN (the agent's owner). ALTER preserves existing threads;
-- CREATE OR REPLACE would discard them.

USE ROLE SUPPLYCHAIN;
USE WAREHOUSE COMPUTE_WH;

ALTER AGENT SCS.SEMANTIC.SCM_KG_CHATBOT SET FROM SPECIFICATION $$
{
  "models": {
    "orchestration": "auto"
  },
  "instructions": {
    "response": "You are a supply-chain analyst assistant answering questions about the Asterion Devices supply chain. Answer with findings only \u2014 no narration of your own steps. Present rankings, breakdowns and trends as a markdown table with a header row, a separator row, and no blank lines between rows. Express monetary figures in USD. Refer to time periods by calendar date, never by week number.",
    "orchestration": "Use the supply_chain_kg tool for anything about entities and their relationships \u2014 suppliers, supplier sites, parts, products, plants, warehouses, customers, lanes, ports, carriers and countries \u2014 including graph analytics such as importance (PAGERANK), connectivity (DEGREE_TOTAL), bottlenecks (BETWEENNESS) and communities (COMPONENT_ID). Use the supply_chain_docs tool for questions about contracts, non-conformance reports, supplier scorecards and risk alerts. Always execute the SQL you generate with sql_exec and answer from the rows it returns \u2014 never present un-executed SQL as the answer.",
    "sample_questions": [
      "Which are the most critical suppliers in the supply chain?",
      "Which supplier sites are single points of failure?",
      "Which parts have the most alternate approved sources?",
      "Give me a summary of the knowledge graph"
    ]
  },
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "supply_chain_kg",
        "description": "Supply-chain knowledge graph: nodes (suppliers, supplier sites, parts, products, plants, warehouses, customers, lanes, ports, carriers, countries, commodities) and the edges between them, with precomputed PageRank, degree, HITS hub/authority, betweenness and connected components."
      }
    },
    {
      "tool_spec": {
        "type": "cortex_search",
        "name": "supply_chain_docs",
        "description": "Unstructured supply-chain documents: supplier contracts, non-conformance reports, supplier scorecards and risk alerts."
      }
    },
    {
      "tool_spec": {
        "type": "sql_exec",
        "name": "sql_exec"
      }
    },
    {
      "tool_spec": {
        "type": "data_to_chart",
        "name": "data_to_chart"
      }
    }
  ],
  "tool_resources": {
    "supply_chain_kg": {
      "semantic_view": "SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG"
    },
    "supply_chain_docs": {
      "name": "SCS.SEMANTIC.SCM_DOCUMENT_SEARCH",
      "max_results": 5
    },
    "sql_exec": {
      "type": "warehouse",
      "name": "COMPUTE_WH"
    }
  }
}
$$;

-- Verify: agent_spec should no longer be empty.
DESCRIBE AGENT SCS.SEMANTIC.SCM_KG_CHATBOT;
