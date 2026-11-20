"""
Lakehouse vs Warehouse - working demo in Python (Streamlit)
===========================================================
COSC-5606 Group 16: Yuqi Xiao, Sahil Kumar, Rohit Bhatti.

Run it with:
    pip install streamlit      (only once)
    streamlit run lakehouse_demo.py

HOW IT WORKS: there is no Run button to press. The result changes the
moment you change ANY option - dataset, system, query, CSV/Parquet or
AQE on/off. The big result line, the SQL and the comparison chart all
update immediately, so you can see the output change with every choice.

EVERY number is a real median of 3 runs from the v1.1 rerun on 20 Nov 2026
(same dataset: 20,000 orders / 100,000 lineitems, seed 42). Nothing is made up.
Spark times here are from the 20 Nov rerun (PySpark 4.3.0, Java 17) - much higher
than the 12 Nov run, so do not mix old and new Spark numbers.

The demo is separate from the project report - it is only for showing
the working model. Do not submit this file as part of the project
unless the group agrees.
"""

import streamlit as st

# ------------------------------------------------------------------
# Real results from the project (medians of 3 runs, milliseconds)
# ------------------------------------------------------------------
POSTGRES = {
    "Balanced": {"Q1": 12.51, "Q2": 42.41, "Q3": 39.83, "Q4": 21.28},
    "Skewed": {"Q1": 12.73, "Q2": 49.13, "Q3": 43.50, "Q4": 25.22},
}
DUCKDB_CSV = {
    "Balanced": {"Q1": 0.98, "Q2": 6.88, "Q3": 5.26, "Q4": 3.10},
    "Skewed": {"Q1": 0.89, "Q2": 4.94, "Q3": 5.61, "Q4": 3.45},
}
DUCKDB_PARQUET = {
    "Balanced": {"Q1": 1.03, "Q2": 5.29, "Q3": 4.12, "Q4": 2.91},
    "Skewed": {"Q1": 0.95, "Q2": 4.92, "Q3": 5.65, "Q4": 2.97},
}
SPARK_OFF = {
    "Balanced": {"Q1": 514.32, "Q2": 2494.75, "Q3": 1625.53, "Q4": 713.51},
    "Skewed": {"Q1": 267.78, "Q2": 1784.78, "Q3": 1267.98, "Q4": 287.86},
}
SPARK_ON = {
    "Balanced": {"Q1": 268.82, "Q2": 593.04, "Q3": 348.43, "Q4": 562.18},
    "Skewed": {"Q1": 311.06, "Q2": 430.04, "Q3": 351.86, "Q4": 416.68},
}

QUERIES = {
    "Q1": ("Aggregation",
           "SELECT COUNT(*), SUM(l_extendedprice) FROM lineitem;"),
    "Q2": ("Join + group by customer, top 10",
           "SELECT o_custkey, SUM(l_extendedprice) AS total\n"
           "FROM orders JOIN lineitem ON o_orderkey = l_orderkey\n"
           "GROUP BY o_custkey ORDER BY total DESC LIMIT 10;"),
    "Q3": ("Group by the skewed key, top 10",
           "SELECT l_orderkey, COUNT(*) AS cnt FROM lineitem\n"
           "GROUP BY l_orderkey ORDER BY cnt DESC LIMIT 10;"),
    "Q4": ("Filter + join + aggregation",
           "SELECT COUNT(*), SUM(l_extendedprice)\n"
           "FROM orders JOIN lineitem ON o_orderkey = l_orderkey\n"
           "WHERE o_orderdate >= '2024-06-01';"),
}

st.set_page_config(page_title="Lakehouse vs Warehouse Demo",
                   layout="centered")
st.title("Lakehouse vs Warehouse under Skewed Data")
st.write("COSC-5606 Group 16 - Yuqi Xiao, Sahil Kumar, Rohit Bhatti")
st.write("Change any option below and the result updates at once. "
         "All times are real medians of 3 runs (ms).")

# ------------------------------------------------------------------
# What skew looks like
# ------------------------------------------------------------------
st.header("What does skew look like?")
st.write(
    "Both datasets have the same 20,000 orders and 100,000 lineitems. "
    "The difference is only how the lineitems are spread over the orders:"
)
st.write(
    "- **Balanced:** every order has exactly **5** lineitems. "
    "No order is special.\n"
    "- **Skewed:** 1% of the orders (keys 1-200) hold **40%** of all "
    "lineitems. The biggest order has **200** lineitems."
)
st.write(
    "So in Q3 (group by order key), the top key has 5 lineitems on the "
    "balanced data and 200 on the skewed data - the same query, but one "
    "group is 40 times bigger. That is what skew looks like."
)
st.bar_chart(
    {"Balanced (top order key)": [5], "Skewed (top order key)": [200]},
)
st.caption("Lineitems in the biggest group (Q3 top key): 5 vs 200.")

# ------------------------------------------------------------------
# The runner - output updates the moment any option changes
# ------------------------------------------------------------------
st.header("Run a query")

dataset = st.selectbox("Dataset", ["Balanced", "Skewed"])
system = st.selectbox("System", ["PostgreSQL", "DuckDB", "Spark"])
query = st.selectbox("Query", ["Q1", "Q2", "Q3", "Q4"],
                     format_func=lambda q: f"{q} - {QUERIES[q][0]}")

duck_source = None
spark_aqe = None
if system == "DuckDB":
    duck_source = st.radio("DuckDB reads from", ["CSV", "Parquet"],
                           horizontal=True)
if system == "Spark":
    spark_aqe = st.radio("Spark Adaptive Query Execution (AQE)",
                         ["OFF", "ON"], horizontal=True)

# The result for the current choice - recomputed on every change.
if system == "PostgreSQL":
    time_ms = POSTGRES[dataset][query]
    detail = "PostgreSQL 16, database lakehouse_yuqi"
elif system == "DuckDB":
    table = DUCKDB_PARQUET if duck_source == "Parquet" else DUCKDB_CSV
    time_ms = table[dataset][query]
    detail = f"DuckDB on {duck_source} files"
else:
    table = SPARK_ON if spark_aqe == "ON" else SPARK_OFF
    time_ms = table[dataset][query]
    detail = f"Spark 4.3.0 local mode, AQE {spark_aqe}"

# Big result line: this is the output that changes with every choice.
st.success(f"**{query} on {system} ({dataset}): {time_ms} ms**  — {detail}")
st.code(QUERIES[query][1], language="sql")

# Compare all systems for this query + dataset (also updates live).
compare = {
    "PostgreSQL": POSTGRES[dataset][query],
    "DuckDB (CSV)": DUCKDB_CSV[dataset][query],
    "DuckDB (Parquet)": DUCKDB_PARQUET[dataset][query],
    "Spark AQE OFF": SPARK_OFF[dataset][query],
    "Spark AQE ON": SPARK_ON[dataset][query],
}
st.write(f"All systems, {query} on {dataset} data (ms):")
st.bar_chart(compare)

# ------------------------------------------------------------------
# Full results table
# ------------------------------------------------------------------
st.header("All results (ms, medians of 3 runs)")
st.write("PostgreSQL")
st.table(POSTGRES)
st.write("DuckDB - CSV")
st.table(DUCKDB_CSV)
st.write("DuckDB - Parquet")
st.table(DUCKDB_PARQUET)
st.write("Spark - AQE OFF")
st.table(SPARK_OFF)
st.write("Spark - AQE ON")
st.table(SPARK_ON)

st.header("Findings")
st.write(
    "- DuckDB is the fastest on every query (about 1-7 ms), because it "
    "reads columnar data straight from the file.\n"
    "- PostgreSQL is steady (about 13-49 ms); skew slows Q2 by 16%, "
    "Q3 by 9%, Q4 by 19%, Q1 barely changes (+2%).\n"
    "- Spark is the slowest, but AQE cuts Q2/Q3 by 72-79% - except "
    "skewed Q1 (268 -> 311 ms) and skewed Q4 (288 -> 417 ms), which "
    "are slower with AQE on.\n"
    "- Skew hits Q3 hardest in DuckDB Parquet (+37%), because one group "
    "becomes 40 times bigger."
)
