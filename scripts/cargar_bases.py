import json
import re
import time
from pathlib import Path

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

NOMBRE = "documentos_unah"
DIM = 384

# Categoría temática por documento
CATEGORIAS = {
    "Manual de Procedimientos Académicos UNAH": "Procedimientos académicos",
    "Normas-Academica-de-la-UNAH": "Normas académicas",
    "Reglamento-de-los-Estudiantes-de-la-UNAH-Comisionado-Universitario": "Reglamento estudiantil",
}

# 1. Cargar datos
fragmentos = json.loads(Path("datos_procesados/embeddings_info.json").read_text(encoding="utf-8"))
vectores = np.load("datos_procesados/embeddings.npy")
assert len(fragmentos) == len(vectores), "La cantidad de fragmentos y vectores no coincide"

# Completar metadatos: categoría y página de origen
ultima_pagina = {}
for f in fragmentos:
    f["categoria"] = CATEGORIAS.get(f["documento"], f["categoria"])
    paginas = re.findall(r"---\s*Página\s*(\d+)\s*---", f["contenido"])
    if f["contenido"].lstrip().startswith("--- Página") and paginas:
        f["pagina"] = int(paginas[0])
    else:
        f["pagina"] = ultima_pagina.get(f["documento"], int(paginas[0]) if paginas else 0)
    if paginas:
        ultima_pagina[f["documento"]] = int(paginas[-1])

print(f"Datos cargados: {len(fragmentos)} fragmentos | Vectores: {vectores.shape}\n")

# 2. PostgreSQL con pgvector
inicio = time.perf_counter()
conn = psycopg2.connect(host="localhost", port=5432, dbname="vectordb",
                        user="admin", password="adminpassword")
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()
register_vector(conn)

cur.execute(f"DROP TABLE IF EXISTS {NOMBRE};")
cur.execute(f"""
    CREATE TABLE {NOMBRE} (
        id        VARCHAR(20) PRIMARY KEY,
        vector    vector({DIM}) NOT NULL,
        contenido TEXT NOT NULL,
        documento TEXT NOT NULL,
        categoria TEXT NOT NULL,
        fuente    TEXT NOT NULL,
        pagina    INTEGER
    );
""")
execute_values(
    cur,
    f"INSERT INTO {NOMBRE} (id, vector, contenido, documento, categoria, fuente, pagina) VALUES %s",
    [(f["id"], v, f["contenido"], f["documento"], f["categoria"], f["fuente"], f["pagina"])
     for f, v in zip(fragmentos, vectores)],
)
# Índice HNSW con la métrica del coseno
cur.execute(f"CREATE INDEX {NOMBRE}_hnsw ON {NOMBRE} USING hnsw (vector vector_cosine_ops);")
conn.commit()
cur.execute(f"SELECT COUNT(*) FROM {NOMBRE};")
total_pg = cur.fetchone()[0]
conn.close()
print(f"[PostgreSQL pgvector] Tabla '{NOMBRE}' + índice HNSW (coseno) | Registros: {total_pg} | Tiempo: {time.perf_counter() - inicio:.2f} s")

# 3. ChromaDB
inicio = time.perf_counter()
chroma = chromadb.HttpClient(host="localhost", port=8000)
try:
    chroma.delete_collection(NOMBRE)
except Exception:
    pass
coleccion = chroma.create_collection(name=NOMBRE, metadata={"hnsw:space": "cosine"})
coleccion.add(
    ids=[f["id"] for f in fragmentos],
    embeddings=vectores.tolist(),
    documents=[f["contenido"] for f in fragmentos],
    metadatas=[{"documento": f["documento"], "categoria": f["categoria"],
                "fuente": f["fuente"], "pagina": f["pagina"]} for f in fragmentos],
)
print(f"[ChromaDB]            Colección '{NOMBRE}' (HNSW, coseno) | Registros: {coleccion.count()} | Tiempo: {time.perf_counter() - inicio:.2f} s")

# 4. Qdrant
inicio = time.perf_counter()
qdrant = QdrantClient(host="localhost", port=6333)
if qdrant.collection_exists(NOMBRE):
    qdrant.delete_collection(NOMBRE)
qdrant.create_collection(
    collection_name=NOMBRE,
    vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
)
qdrant.upsert(
    collection_name=NOMBRE,
    points=[PointStruct(id=i, vector=v.tolist(),
                        payload={"id": f["id"], "contenido": f["contenido"], "documento": f["documento"],
                                 "categoria": f["categoria"], "fuente": f["fuente"], "pagina": f["pagina"]})
            for i, (f, v) in enumerate(zip(fragmentos, vectores))],
    wait=True,
)
total_q = qdrant.count(NOMBRE, exact=True).count
print(f"[Qdrant]              Colección '{NOMBRE}' (HNSW, coseno) | Registros: {total_q} | Tiempo: {time.perf_counter() - inicio:.2f} s")
