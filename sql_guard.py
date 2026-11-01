import re

ALLOWED_COLUMNS = {
    "roll_number", "name", "vertical_name", "course_name",
    "date", "start_time", "end_time", "venue_name", "status"
}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|"
    r"copy|call|execute|do|merge|refresh|vacuum|analyze|set|reset|"
    r"pg_sleep|information_schema|pg_catalog)\b", re.I
)

def validate_sql(sql: str) -> str:
    sql = sql.strip().strip("`")
    sql = re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.I).strip()
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if ";" in sql.rstrip(";"):
        raise ValueError("Only one SQL statement is allowed.")
    sql = sql.rstrip(";")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a forbidden operation or system catalog.")
    if not re.search(r"\bps_cleared_course_view\b", sql, re.I):
        raise ValueError("Query must use the approved dataset.")
    if not re.search(r"\blimit\s+\d+\b", sql, re.I):
        sql += " LIMIT 50"
    m = re.search(r"\blimit\s+(\d+)\b", sql, re.I)
    if m and int(m.group(1)) > 100:
        sql = sql[:m.start(1)] + "100" + sql[m.end(1):]
    return sql
