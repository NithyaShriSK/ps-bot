"""Optional pgvector semantic index for course/vertical names.
Requires sentence-transformers and the course_embeddings table from schema.sql.
"""
from sentence_transformers import SentenceTransformer
from db import connect

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def main():
    model = SentenceTransformer(MODEL_NAME)  # downloads model on first run
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT vertical_name, course_name
                FROM ps_cleared_course_view
            """)
            pairs = cur.fetchall()
        batch=[]
        for vertical, course in pairs:
            text=f"Vertical: {vertical}. Course or skill: {course}"
            batch.append((vertical, course, text))
        texts=[x[2] for x in batch]
        vectors=model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        with conn.cursor() as cur:
            for i, (vertical, course, _) in enumerate(batch):
                vector = "[" + ",".join(f"{float(v):.8f}" for v in vectors[i]) + "]"
                cur.execute("""
                    INSERT INTO course_embeddings(vertical_name, course_name, embedding)
                    VALUES (%s,%s,%s::vector)
                    ON CONFLICT (vertical_name, course_name)
                    DO UPDATE SET embedding=EXCLUDED.embedding
                """, (vertical, course, vector))
                if i and i % 500 == 0:
                    print(f"Indexed {i:,}/{len(batch):,}")
    print(f"Indexed {len(batch):,} distinct course/vertical pairs.")

if __name__ == "__main__":
    main()
