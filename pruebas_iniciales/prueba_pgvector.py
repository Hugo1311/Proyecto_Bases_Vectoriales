import time
import psycopg2
from sentence_transformers import SentenceTransformer
from datos import documentos, pregunta

modelo = SentenceTransformer("all-MiniLM-L6-v2")

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="vectordb",
    user="admin",
    password="adminpassword"
)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS prueba_inicial;")
cur.execute("""
    CREATE TABLE prueba_inicial (
        id SERIAL PRIMARY KEY,
        texto TEXT,
        vector vector(384)
    );
""")

embeddings = modelo.encode(documentos)
for texto, vec in zip(documentos, embeddings):
    cur.execute(
        "INSERT INTO prueba_inicial (texto, vector) VALUES (%s, %s);",
        (texto, str(vec.tolist()))
    )
conn.commit()

vec_pregunta = str(modelo.encode(pregunta).tolist())

inicio = time.perf_counter()
cur.execute("""
    SELECT texto, 1 - (vector <=> %s::vector) AS similitud
    FROM prueba_inicial
    ORDER BY vector <=> %s::vector
    LIMIT 3;
""", (vec_pregunta, vec_pregunta))
resultados = cur.fetchall()
tiempo_ms = (time.perf_counter() - inicio) * 1000

print(f"=== PostgreSQL (pgvector) | Tiempo de consulta: {tiempo_ms:.2f} ms ===")
for texto, score in resultados:
    print(f"Documento: {texto}\nSimilitud: {score:.4f}\n")

cur.close()
conn.close()