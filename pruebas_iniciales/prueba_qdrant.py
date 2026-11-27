import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from datos import documentos, pregunta

modelo = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(host="localhost", port=6333)

if client.collection_exists("prueba_inicial"):
    client.delete_collection("prueba_inicial")

client.create_collection(
    collection_name="prueba_inicial",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

embeddings = modelo.encode(documentos)
puntos = [
    PointStruct(id=i, vector=vec.tolist(), payload={"texto": texto})
    for i, (texto, vec) in enumerate(zip(documentos, embeddings))
]
client.upsert(collection_name="prueba_inicial", points=puntos)

vec_pregunta = modelo.encode(pregunta).tolist()

inicio = time.perf_counter()
resultados = client.query_points(
    collection_name="prueba_inicial",
    query=vec_pregunta,
    limit=3
).points
tiempo_ms = (time.perf_counter() - inicio) * 1000

print(f"=== Qdrant | Tiempo de consulta: {tiempo_ms:.2f} ms ===")
for r in resultados:
    print(f"Documento: {r.payload['texto']}\nSimilitud: {r.score:.4f}\n")