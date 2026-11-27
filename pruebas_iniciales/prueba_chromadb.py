import time
import chromadb
from sentence_transformers import SentenceTransformer
from datos import documentos, pregunta

modelo = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.HttpClient(host="localhost", port=8000)

try:
    client.delete_collection("prueba_inicial")
except Exception:
    pass

coleccion = client.create_collection(
    name="prueba_inicial",
    metadata={"hnsw:space": "cosine"}
)

embeddings = modelo.encode(documentos).tolist()
ids = [str(i) for i in range(len(documentos))]
coleccion.add(ids=ids, documents=documentos, embeddings=embeddings)

vec_pregunta = modelo.encode([pregunta]).tolist()

inicio = time.perf_counter()
resultados = coleccion.query(query_embeddings=vec_pregunta, n_results=3)
tiempo_ms = (time.perf_counter() - inicio) * 1000

print(f"=== ChromaDB | Tiempo de consulta: {tiempo_ms:.2f} ms ===")
for texto, dist in zip(resultados["documents"][0], resultados["distances"][0]):
    print(f"Documento: {texto}\nSimilitud: {1 - dist:.4f}\n")