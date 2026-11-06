import json
from query_engine import process_query

def main():
    print("========================================")
    print("SkillQuery Student Skills Assistant CLI")
    print("Type a question, or 'exit' / 'clear'.")
    print("========================================")
    test_user_id = "LOCAL_CLI_USER"

    while True:
        try:
            question = input("\nQuestion: ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue

            result = process_query(test_user_id, question)
            print(f"\n{result['answer']}")
            
            if result.get("rows"):
                print(f"\n--- Data Table ({len(result['rows'])} rows) ---")
                cols = result["columns"]
                print(" | ".join(cols))
                print("-" * 50)
                for row in result["rows"][:5]:
                    print(" | ".join(str(row.get(c, "")) for c in cols))
                if len(result["rows"]) > 5:
                    print(f"... and {len(result['rows']) - 5} more rows.")

            meta = result.get("meta", {})
            if meta.get("sql"):
                print(f"\n[SQL Used]: {meta['sql'].strip().replace(chr(10), ' ')}")

        except Exception as error:
            print(f"\nRequest failed: {type(error).__name__}: {error}")

if __name__ == "__main__":
    main()
