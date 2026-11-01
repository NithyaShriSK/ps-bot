"""Import the supplied MySQL-style INSERT dump into PostgreSQL.
Usage: python import_mysql_dump.py "C:\\path\\ps_cleared_data.sql"
"""
import sys, re
from pathlib import Path
from db import connect

TABLE = "ps_cleared_course_view"
COLS = ("roll_number","name","vertical_name","course_name","date","start_time","end_time","venue_name","status")

def split_values(row):
    out, buf, quoted, i = [], [], False, 0
    while i < len(row):
        ch = row[i]
        if ch == "'":
            if quoted and i + 1 < len(row) and row[i+1] == "'":
                buf.append("'"); i += 2; continue
            quoted = not quoted
        elif ch == "\\" and quoted and i + 1 < len(row):
            i += 1; buf.append(row[i])
        elif ch == "," and not quoted:
            out.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf).strip())
    vals=[]
    for x in out:
        if x.upper() == "NULL": vals.append(None)
        elif len(x)>=2 and x[0]=="'" and x[-1]=="'": vals.append(x[1:-1])
        else: vals.append(x)
    return vals

def tuples_from_values(text):
    i=0; n=len(text)
    while i<n:
        if text[i] != "(":
            i+=1; continue
        i+=1; start=i; quoted=False
        while i<n:
            ch=text[i]
            if ch=="'" and (i==0 or text[i-1]!="\\"):
                if quoted and i+1<n and text[i+1]=="'":
                    i+=2; continue
                quoted=not quoted
            elif ch==")" and not quoted:
                yield text[start:i]
                i+=1; break
            i+=1

def main(path):
    content=Path(path).read_text(encoding="utf-8", errors="replace")
    # Create the PostgreSQL table first by running schema.sql separately.
    pattern = re.compile(r"insert\s+into\s+`ps_cleared_course_view`\s*\([^)]*\)\s*values\s*", re.I)
    total=0
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE ps_cleared_course_view")
            for match in pattern.finditer(content):
                end=content.find(";", match.end())
                if end<0: end=len(content)
                block=content[match.end():end]
                batch=[]
                for raw in tuples_from_values(block):
                    vals=split_values(raw)
                    if len(vals)!=9:
                        raise ValueError(f"Expected 9 values, got {len(vals)}: {vals[:2]}")
                    batch.append(vals)
                    if len(batch)>=1000:
                        cur.executemany(
                            "INSERT INTO ps_cleared_course_view "
                            "(roll_number,name,vertical_name,course_name,date,start_time,end_time,venue_name,status) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", batch)
                        total+=len(batch); batch=[]
                if batch:
                    cur.executemany(
                        "INSERT INTO ps_cleared_course_view "
                        "(roll_number,name,vertical_name,course_name,date,start_time,end_time,venue_name,status) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", batch)
                    total+=len(batch)
                print(f"Imported {total:,} rows so far...")
    print(f"Done. Imported {total:,} rows.")

if __name__=="__main__":
    if len(sys.argv)!=2:
        print('Usage: python import_mysql_dump.py "path/to/ps_cleared_data.sql"')
        raise SystemExit(2)
    main(sys.argv[1])
