# Actividad 5: búsqueda semántica con similitud del coseno en las tres bases
# Uso: python scripts\buscar.py "pregunta" [K]

import sys
import time

import psycopg2
from pgvector.psycopg2 import register_vector
import chromadb
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

NOMBRE = "documentos_unah"
pregunta = sys.argv[1] if len(sys.argv) > 1 else "¿Qué sucede cuando repruebo una asignatura por segunda vez?"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 3

# El modelo e5 exige el prefijo "query: " en las preguntas ("passage: " ya se usó en los fragmentos)
modelo = SentenceTransformer("intfloat/multilingual-e5-small")
vector = modelo.encode("query: " + pregunta, normalize_embeddings=True)

print(f'Pregunta: "{pregunta}" | K = {K}\n')


def mostrar(nombre, ms, filas):
    print(f"=== {nombre} | Tiempo de consulta: {ms:.2f} ms ===")
    for i, (id_, sim, doc, pag, texto) in enumerate(filas, start=1):
        extracto = " ".join(texto.split())[:160]
        print(f"{i}. [{id_}] similitud={sim:.4f} | {doc} (pág. {pag})\n   {extracto}...")
    print()


# PostgreSQL con pgvector (<=> = distancia coseno)
conn = psycopg2.connect(host="localhost", port=5432, dbname="vectordb",
                        user="admin", password="adminpassword")
register_vector(conn)
cur = conn.cursor()
inicio = time.perf_counter()
cur.execute(f"""
    SELECT id, 1 - (vector <=> %s) AS similitud, documento, pagina, contenido
    FROM {NOMBRE} ORDER BY vector <=> %s LIMIT %s;
""", (vector, vector, K))
filas = cur.fetchall()
mostrar("PostgreSQL (pgvector)", (time.perf_counter() - inicio) * 1000, filas)
conn.close()

# ChromaDB (devuelve distancia coseno = 1 - similitud)
coleccion = chromadb.HttpClient(host="localhost", port=8000).get_collection(NOMBRE)
inicio = time.perf_counter()
r = coleccion.query(query_embeddings=[vector.tolist()], n_results=K)
ms = (time.perf_counter() - inicio) * 1000
mostrar("ChromaDB", ms, [(i, 1 - d, m["documento"], m["pagina"], t)
                         for i, d, m, t in zip(r["ids"][0], r["distances"][0], r["metadatas"][0], r["documents"][0])])

# Qdrant (devuelve la similitud coseno directamente)
qdrant = QdrantClient(host="localhost", port=6333)
inicio = time.perf_counter()
r = qdrant.query_points(collection_name=NOMBRE, query=vector.tolist(), limit=K).points
ms = (time.perf_counter() - inicio) * 1000
mostrar("Qdrant", ms, [(p.payload["id"], p.score, p.payload["documento"], p.payload["pagina"], p.payload["contenido"])
                       for p in r])
