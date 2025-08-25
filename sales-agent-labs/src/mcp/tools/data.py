from __future__ import annotations
import os, re, json, hashlib, pathlib, io, time
from typing import Dict, Any, Optional, List
import duckdb, pandas as pd
import matplotlib.pyplot as plt

from src.common.jsonlog import jlog
from src.common.config import cfg
from src.data.catalog import parquet_path_for

# --- LLM helpers (Gemini 2.0 Flash) ---
_USE_LLM = True
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except Exception:
    _USE_LLM = False


def _gemini():
    c = cfg()
    project = c.get("project", {}).get("id") or os.getenv("GOOGLE_CLOUD_PROJECT")
    region = c.get("project", {}).get("region") or os.getenv(
        "GOOGLE_CLOUD_REGION", "us-central1"
    )
    model_name = c.get("llm", {}).get("model", "models/gemini-2.0-flash-001")
    vertexai.init(project=project, location=region)
    return GenerativeModel(model_name)


_SQL_GUARD = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|MERGE)\b", re.I
)


def _nl2sql(question: str, columns: List[Dict[str, str]]) -> str:
    # Enhanced pattern matching for common question types
    question_lower = question.lower().strip()
    col_names = [c["name"] for c in columns]
    
    # Pattern-based SQL generation for reliability
    patterns = [
        # Group by patterns (more specific, check first)
        (r'\b(\w+)\s+by\s+(\w+)', lambda m: _build_group_by_query(m.group(1), m.group(2), col_names)),
        (r'\btop\s+(\d+)\s+(\w+)', lambda m: _build_top_n_query(int(m.group(1)), m.group(2), col_names)),
        # Total/sum patterns  
        (r'\b(?:total|sum)\s+(\w+)', lambda m: _build_sum_query(m.group(1), col_names)),
        (r'\baverage|avg\s+(\w+)', lambda m: _build_avg_query(m.group(1), col_names)),
    ]
    
    # Try pattern matching first
    for pattern, builder in patterns:
        match = re.search(pattern, question_lower)
        if match:
            try:
                return builder(match)
            except Exception:
                continue
    
    # Fallback to LLM or heuristic
    if not _USE_LLM:
        return _fallback_query(columns)

    try:
        llm_start_time = time.time()
        schema_str = "\n".join([f"- {c['name']} ({c['dtype']})" for c in columns])
        prompt = f"""
You are a SQL generator for DuckDB. Given a table t with columns:
{schema_str}

Write a single SELECT (or WITH ... SELECT) that answers the question:
Q: {question}

Rules:
- Only SELECT/WITH, no DDL/DML.
- Column names are case-sensitive: {', '.join(col_names)}
- Prefer aggregates and top-10 where appropriate.
- If no obvious grouping, return the most informative rows.
- Always include a LIMIT 5000 at the end if not present.
- Use exact column names from the schema above.

Return ONLY the SQL, nothing else.
"""
        model = _gemini()
        resp = model.generate_content(prompt)
        llm_time = time.time() - llm_start_time
        sql = resp.text.strip().strip("```sql").strip("```").replace("```", "").strip()
        
        # Clean and validate
        if not re.search(r"\blimit\b", sql, re.I):
            sql = sql.rstrip(";") + " LIMIT 5000"
            
        # Log LLM performance for monitoring
        import logging
        log = logging.getLogger("nl2sql")
        log.info(f"LLM SQL generation took {llm_time:.1f}s for question: {question[:50]}...")
            
        return sql
        
    except Exception as e:
        llm_time = time.time() - llm_start_time
        import logging
        log = logging.getLogger("nl2sql") 
        log.warning(f"LLM SQL fallback after {llm_time:.1f}s, error: {str(e)}")
        return _fallback_query(columns)


def _build_sum_query(target_col: str, col_names: List[str]) -> str:
    # Find best matching numeric column
    target = _find_best_column_match(target_col, col_names)
    return f"SELECT SUM({target}) as total_{target} FROM t"

def _build_group_by_query(measure_col: str, group_col: str, col_names: List[str]) -> str:
    measure = _find_best_column_match(measure_col, col_names)  
    group = _find_best_column_match(group_col, col_names)
    return f"SELECT {group}, SUM({measure}) as total_{measure} FROM t GROUP BY {group} ORDER BY 2 DESC LIMIT 10"

def _build_top_n_query(n: int, col: str, col_names: List[str]) -> str:
    target = _find_best_column_match(col, col_names)
    return f"SELECT * FROM t ORDER BY {target} DESC LIMIT {min(n, 100)}"

def _build_avg_query(target_col: str, col_names: List[str]) -> str:
    target = _find_best_column_match(target_col, col_names)
    return f"SELECT AVG({target}) as avg_{target} FROM t"

def _find_best_column_match(target: str, col_names: List[str]) -> str:
    target_lower = target.lower()
    
    # Special mappings
    mappings = {
        'sales': ['total', 'revenue', 'amount', 'sales'],
        'total': ['total', 'amount', 'revenue', 'sales'],
        'revenue': ['total', 'revenue', 'amount', 'sales'], 
        'company': ['company', 'customer', 'client', 'name'],
        'companies': ['company', 'customer', 'client', 'name'],
    }
    
    # Check mappings first
    if target_lower in mappings:
        for preferred in mappings[target_lower]:
            for col in col_names:
                if preferred.lower() in col.lower():
                    return col
    
    # Exact match 
    for col in col_names:
        if col.lower() == target_lower:
            return col
    
    # Partial match
    for col in col_names:
        if target_lower in col.lower() or col.lower() in target_lower:
            return col
    
    # Default to first column if no match
    return col_names[0] if col_names else "id"

def _fallback_query(columns: List[Dict[str, str]]) -> str:
    # Enhanced fallback logic
    cat = next(
        (
            c["name"]
            for c in columns
            if not any(k in c["dtype"] for k in ["int", "float", "double", "decimal"])
        ),
        None,
    )
    num = next(
        (
            c["name"]
            for c in columns
            if any(k in c["dtype"] for k in ["int", "float", "double", "decimal"])
        ),
        None,
    )
    if cat and num:
        return f"SELECT {cat} AS category, SUM({num}) AS value FROM t GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
    # last resort
    return "SELECT * FROM t LIMIT 50"


def _sanitize_sql(sql: str) -> str:
    s = re.sub(r"--.*?$", "", sql, flags=re.M)  # strip line comments
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)  # strip block comments
    if _SQL_GUARD.search(s):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    return s


def _chart_png_path(dataset_id: str, question: str) -> pathlib.Path:
    h = hashlib.sha256(question.encode("utf-8")).hexdigest()[:8]
    p = pathlib.Path("out/images/charts") / dataset_id
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{h}.png"


def _to_table_md(df: pd.DataFrame, max_rows: int = 12, max_cols: int = 6) -> str:
    df = df.iloc[:max_rows, :max_cols]
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join([header, sep] + rows)


def _choose_chart(df: pd.DataFrame) -> str:
    # Enhanced chart selection logic with better coverage
    cols = df.columns.tolist()
    rows = len(df)
    
    # Single value results (like AVG, SUM) - create a simple bar chart
    if len(cols) == 1 and rows == 1:
        return "single_value_bar"
    
    # Multi-row, single column (like top companies) - bar chart
    if len(cols) == 1 and rows > 1:
        return "single_col_bar" 
        
    # Two or more columns with multiple rows
    if len(cols) >= 2 and rows > 1:
        x = cols[0]
        y = cols[1]
        
        # Check if we have a numeric column for Y-axis
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) >= 1:
            # Use first numeric column as Y if current Y isn't numeric
            if not pd.api.types.is_numeric_dtype(df[y]) and numeric_cols:
                y = numeric_cols[0]
                
            # line if datetime-like X, else bar
            if pd.api.types.is_datetime64_any_dtype(df[x]) or "date" in str(df[x].dtype):
                return "line"
            return "bar"
    
    # Two columns with few rows (<=10) - still worth charting
    if len(cols) == 2 and rows <= 10 and rows > 0:
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) >= 1:
            return "bar"
    
    # Single column with reasonable number of rows
    if len(cols) == 1 and 1 < rows <= 20:
        return "single_col_bar"
    
    # Fallback to table for complex data
    return "table"


def _render_chart(df: pd.DataFrame, path: pathlib.Path) -> Optional[pathlib.Path]:
    kind = _choose_chart(df)
    if kind == "table":
        return None
    
    plt.figure(figsize=(8, 4.5))  # 16:9
    
    try:
        if kind == "single_value_bar":
            # Single aggregate value - create a simple bar chart
            col = df.columns[0]
            value = df.iloc[0, 0]
            plt.bar([col.replace('_', ' ').title()], [value])
            plt.ylabel('Value')
            plt.title(f'{col.replace("_", " ").title()}: {value:,.0f}')
            
        elif kind == "single_col_bar":
            # Multiple values in one column - use index as x-axis
            col = df.columns[0]
            plt.bar(range(len(df)), df[col])
            plt.ylabel(col.replace('_', ' ').title())
            plt.xlabel('Item')
            
        elif kind == "line":
            # Time series or date-based data
            x = df.columns[0]
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            y = numeric_cols[0] if numeric_cols else df.columns[1]
            plt.plot(df[x], df[y])
            plt.xlabel(x.replace('_', ' ').title())
            plt.ylabel(y.replace('_', ' ').title())
            
        else:  # "bar" - default case
            # Two columns: category and value
            x = df.columns[0]
            # Find the numeric column for Y-axis
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if numeric_cols:
                y = numeric_cols[0]  # Use first numeric column
            else:
                y = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            
            plt.bar(df[x].astype(str), df[y])
            plt.xlabel(x.replace('_', ' ').title())
            plt.ylabel(y.replace('_', ' ').title())
            plt.xticks(rotation=30, ha="right")
    
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        return path
        
    except Exception as e:
        plt.close()  # Ensure we clean up the figure
        raise e


def _insights(df: pd.DataFrame, question: str) -> List[str]:
    # Minimal heuristic; if LLM available, summarize top rows concisely
    if not _USE_LLM:
        return [f"Answered: {question}", f"Rows: {len(df)}; Columns: {len(df.columns)}"]
    
    try:
        llm_start_time = time.time()
        sample = df.head(10).to_csv(index=False)
        prompt = f"""
Given this question and CSV sample rows, write 2-4 short, factual bullets (<= 350 chars total).

Q: {question}

CSV:
{sample}
"""
        model = _gemini()
        resp = model.generate_content(prompt)
        llm_time = time.time() - llm_start_time
        
        # Log LLM performance
        import logging
        log = logging.getLogger("insights")
        log.info(f"LLM insights generation took {llm_time:.1f}s for question: {question[:50]}...")
        
        text = resp.text.strip().splitlines()
        bullets = [re.sub(r"^[\-\*\d\.\s]+", "", ln).strip() for ln in text if ln.strip()]
        bullets = [b for b in bullets if b][:4]
        return bullets or [f"Result has {len(df)} rows."]
        
    except Exception as e:
        # Fallback to simple insights if LLM fails
        import logging
        log = logging.getLogger("insights")
        log.warning(f"LLM insights fallback, error: {str(e)}")
        return [f"Answered: {question}", f"Found {len(df)} results with {len(df.columns)} columns"]


def data_query_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Params: {dataset_id, question, sheet?, limit_rows?, req_id?}
    """
    from src.common.jsonlog import jlog
    import logging
    
    log = logging.getLogger("data_query_tool")
    
    dataset_id = params.get("dataset_id")
    question = params.get("question") or ""
    sheet = params.get("sheet")
    limit_rows = int(params.get("limit_rows") or 100_000)
    req_id = params.get("req_id")  # Accept req_id from orchestrator

    if not dataset_id or not question:
        raise ValueError("dataset_id and question are required")

    try:
        start_time = time.time()
        jlog(log, logging.INFO, event="data_query_begin", 
             dataset_id=dataset_id, question=question, sheet=sheet, req_id=req_id)

        # Phase 1: Load data
        load_start = time.time()
        pq = parquet_path_for(dataset_id, sheet)
        df = pd.read_parquet(pq)
        cols = [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns]
        load_time = time.time() - load_start

        jlog(log, logging.INFO, event="data_loaded", 
             rows=len(df), columns=len(df.columns), load_time_secs=load_time, req_id=req_id)

        # Phase 2: Generate SQL
        sql_start = time.time()
        sql = _nl2sql(question, cols)
        sql = _sanitize_sql(sql)
        sql_gen_time = time.time() - sql_start
        
        jlog(log, logging.INFO, event="sql_generated", sql=sql[:200], sql_gen_time_secs=sql_gen_time, req_id=req_id)

        # Phase 3: Execute query
        query_start = time.time()
        con = duckdb.connect()
        con.register("t", df)
        try:
            con.execute("EXPLAIN " + sql)
        except Exception as e:
            jlog(log, logging.WARNING, event="sql_validation_failed", 
                 sql=sql, error=str(e), req_id=req_id)
            # Try a safer fallback query
            sql = f"SELECT * FROM t LIMIT {min(50, limit_rows)}"
            jlog(log, logging.INFO, event="sql_fallback", sql=sql, req_id=req_id)
            
        out_df = con.execute(sql).fetch_df()
        if len(out_df) > limit_rows:
            out_df = out_df.head(limit_rows)
        query_time = time.time() - query_start

        jlog(log, logging.INFO, event="query_executed", 
             result_rows=len(out_df), result_cols=len(out_df.columns), query_time_secs=query_time, req_id=req_id)

        # Phase 4: Generate chart
        chart_start = time.time()
        png_path = _chart_png_path(dataset_id, question)
        try:
            rendered = _render_chart(out_df, png_path)
            chart_time = time.time() - chart_start
            jlog(log, logging.INFO, event="chart_rendered", 
                 path=str(rendered) if rendered else None, chart_time_secs=chart_time, req_id=req_id)
        except Exception as e:
            chart_time = time.time() - chart_start
            jlog(log, logging.WARNING, event="chart_render_failed", error=str(e), chart_time_secs=chart_time, req_id=req_id)
            rendered = None
        
        # Phase 5: Generate table and insights    
        table_start = time.time()
        table_md = _to_table_md(out_df)
        
        try:
            insights = _insights(out_df, question)
            insights_time = time.time() - table_start
        except Exception as e:
            insights_time = time.time() - table_start
            jlog(log, logging.WARNING, event="insights_failed", error=str(e), insights_time_secs=insights_time, req_id=req_id)
            insights = [f"Analysis of {question}", f"Found {len(out_df)} results"]

        total_time = time.time() - start_time
        result = {
            "chart_png_path": str(rendered) if rendered else None,
            "table_md": table_md,
            "insights": insights,
            "sql": sql,
        }
        
        jlog(log, logging.INFO, event="data_query_complete", 
             has_chart=bool(rendered), insights_count=len(insights), 
             total_time_secs=total_time, req_id=req_id)
        
        return result
        
    except Exception as e:
        jlog(log, logging.ERROR, event="data_query_error", 
             dataset_id=dataset_id, question=question, error=str(e), req_id=req_id)
        # Return a minimal fallback result
        return {
            "chart_png_path": None,
            "table_md": f"Error processing query: {question}",
            "insights": [f"Could not process: {question}", f"Error: {str(e)[:100]}"],
            "sql": f"-- Failed: {question}",
        }
