# Evaluación y pruebas en pgvector, ChromaDB y Qdrant
# Requiere haber corrido antes scripts/cargar_bases.py

import json
import re
import statistics
import time
from pathlib import Path

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

NOMBRE = "documentos_unah"
ESCALA = "escala_prueba"
MEDICIONES = 10
FACTORES = [1, 5, 10, 20]   # 503, 2,515, 5,030 y 10,060 registros

# Preguntas de prueba. Un fragmento se considera relevante si contiene alguno de los términos del patrón.
PREGUNTAS = [
    ("¿Qué sucede cuando repruebo una asignatura por segunda vez?", r"reprob|repit|repet|tercera vez|última vez"),
    ("¿Cómo solicito la cancelación de una asignatura?", r"cancelaci[óo]n"),
    ("¿Cuál es el procedimiento para cambiarme de carrera?", r"cambio de carrera"),
    ("¿Cómo se calcula el índice académico?", r"[íi]ndice acad[ée]mico"),
    ("¿Qué debo hacer para reingresar a la universidad?", r"reingres"),
]

Path("resultados").mkdir(exist_ok=True)
resultados = {}

# Conexiones
pg = psycopg2.connect(host="localhost", port=5432, dbname="vectordb", user="admin", password="adminpassword")
register_vector(pg)
cur = pg.cursor()
chroma = chromadb.HttpClient(host="localhost", port=8000)
coleccion = chroma.get_collection(NOMBRE)
qdrant = QdrantClient(host="localhost", port=6333)

modelo = SentenceTransformer("intfloat/multilingual-e5-small")
vectores_preg = modelo.encode(["query: " + p for p, _ in PREGUNTAS], normalize_embeddings=True)


def buscar_pg(vec, k, tabla=NOMBRE, op="<=>"):
    cur.execute(f"SELECT id, contenido FROM {tabla} ORDER BY vector {op} %s LIMIT %s;", (vec, k))
    return cur.fetchall()


def buscar_chroma(vec, k, col=None):
    r = (col or coleccion).query(query_embeddings=[vec.tolist()], n_results=k)
    return list(zip(r["ids"][0], r["documents"][0] if r["documents"] else [""] * k))


def buscar_qdrant(vec, k, col=NOMBRE):
    r = qdrant.query_points(collection_name=col, query=vec.tolist(), limit=k).points
    return [(p.payload["id"], p.payload.get("contenido", "")) for p in r]


BASES = {"PostgreSQL (pgvector)": buscar_pg, "ChromaDB": buscar_chroma, "Qdrant": buscar_qdrant}


def medir(funcion, n=MEDICIONES):
    funcion()
    tiempos = []
    for _ in range(n):
        inicio = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000)
    return {"min_ms": round(min(tiempos), 2), "max_ms": round(max(tiempos), 2),
            "promedio_ms": round(statistics.mean(tiempos), 2), "mediciones_ms": [round(t, 2) for t in tiempos]}


# 1. Relevancia con K = 3, 5 y 10 (precisión@K)
print("=" * 70 + "\n1. RELEVANCIA DE LOS DOCUMENTOS RECUPERADOS (precisión@K)\n" + "=" * 70)
resultados["relevancia"] = {}
for base, buscar in BASES.items():
    resultados["relevancia"][base] = {}
    for k in (3, 5, 10):
        precisiones = []
        for (pregunta, patron), vec in zip(PREGUNTAS, vectores_preg):
            filas = buscar(vec, k)
            relevantes = sum(1 for _, texto in filas if re.search(patron, texto, re.I))
            precisiones.append(relevantes / k)
        resultados["relevancia"][base][f"K={k}"] = {
            "por_pregunta": [round(p, 2) for p in precisiones],
            "promedio": round(statistics.mean(precisiones), 3)}
    r = resultados["relevancia"][base]
    print(f"{base:24} P@3={r['K=3']['promedio']:.3f}  P@5={r['K=5']['promedio']:.3f}  P@10={r['K=10']['promedio']:.3f}")
print("\nDetalle por pregunta (pgvector):")
for i, (pregunta, _) in enumerate(PREGUNTAS):
    r = resultados["relevancia"]["PostgreSQL (pgvector)"]
    print(f"  {pregunta[:55]:57} K3={r['K=3']['por_pregunta'][i]:.2f} K5={r['K=5']['por_pregunta'][i]:.2f} K10={r['K=10']['por_pregunta'][i]:.2f}")

# 2. Comparación de métricas de similitud (pgvector, búsqueda exacta)
print("\n" + "=" * 70 + "\n2. COMPARACIÓN DE MÉTRICAS DE SIMILITUD (K = 10)\n" + "=" * 70)
cur.execute("SET enable_indexscan = off;")  # búsqueda exacta para comparar en igualdad de condiciones
resultados["metricas"] = []
for (pregunta, _), vec in zip(PREGUNTAS, vectores_preg):
    ids = {nombre: [f[0] for f in buscar_pg(vec, 10, op=op)]
           for nombre, op in [("coseno", "<=>"), ("euclidiana_L2", "<->"), ("producto_interno", "<#>")]}
    iguales = ids["coseno"] == ids["euclidiana_L2"] == ids["producto_interno"]
    resultados["metricas"].append({"pregunta": pregunta, "mismo_orden": iguales, "top10": ids})
    print(f"  {pregunta[:55]:57} mismo Top 10 en las 3 métricas: {'Sí' if iguales else 'No'}")
cur.execute("SET enable_indexscan = on;")
print("  (Los vectores están normalizados, por eso coseno, L2 y producto interno ordenan igual.)")

# 3. Tiempo de respuesta: 10 mediciones por base (K = 5)
print("\n" + "=" * 70 + f"\n3. TIEMPO DE RESPUESTA ({MEDICIONES} mediciones por base, K = 5)\n" + "=" * 70)
resultados["tiempos"] = {}
for base, buscar in BASES.items():
    contador = iter(range(10**6))
    t = medir(lambda: buscar(vectores_preg[next(contador) % len(PREGUNTAS)], 5))
    resultados["tiempos"][base] = t
    print(f"{base:24} mín={t['min_ms']:7.2f} ms  máx={t['max_ms']:7.2f} ms  prom={t['promedio_ms']:7.2f} ms")

# 4. Comportamiento de la indexación (pgvector: sin índice vs. HNSW)
print("\n" + "=" * 70 + "\n4. COMPORTAMIENTO DE LA INDEXACIÓN (pgvector, K = 10)\n" + "=" * 70)
vec = vectores_preg[0]
cur.execute(f"EXPLAIN SELECT id FROM {NOMBRE} ORDER BY vector <=> %s LIMIT 10;", (vec,))
plan_con = " | ".join(r[0].strip() for r in cur.fetchall()[:2])
con_indice = medir(lambda: buscar_pg(vec, 10))
ids_hnsw = [f[0] for f in buscar_pg(vec, 10)]
cur.execute("SET enable_indexscan = off;")
cur.execute(f"EXPLAIN SELECT id FROM {NOMBRE} ORDER BY vector <=> %s LIMIT 10;", (vec,))
plan_sin = " | ".join(r[0].strip() for r in cur.fetchall()[:2])
sin_indice = medir(lambda: buscar_pg(vec, 10))
ids_exacto = [f[0] for f in buscar_pg(vec, 10)]
cur.execute("SET enable_indexscan = on;")
recall = len(set(ids_hnsw) & set(ids_exacto)) / 10
resultados["indexacion"] = {"con_hnsw": con_indice, "sin_indice": sin_indice, "recall_hnsw_vs_exacto": recall,
                            "plan_con_indice": plan_con, "plan_sin_indice": plan_sin}
print(f"Con HNSW : prom={con_indice['promedio_ms']:.2f} ms | plan: {plan_con}")
print(f"Sin índice: prom={sin_indice['promedio_ms']:.2f} ms | plan: {plan_sin}")
print(f"Recall@10 de HNSW frente a la búsqueda exacta: {recall:.2f}")

# 5. Comportamiento al incrementar la cantidad de registros
print("\n" + "=" * 70 + "\n5. COMPORTAMIENTO AL INCREMENTAR LOS REGISTROS (K = 5)\n" + "=" * 70)
base_vectores = np.load("datos_procesados/embeddings.npy")
rng = np.random.default_rng(42)
resultados["escalabilidad"] = []
print(f"{'Registros':>10} | {'Base':24} | {'Carga (s)':>9} | {'Consulta prom. (ms)':>19}")
for factor in FACTORES:
    # Copias de los vectores reales con un pequeño ruido, para simular más documentos
    copias = [base_vectores] + [base_vectores + rng.normal(0, 0.02, base_vectores.shape) for _ in range(factor - 1)]
    datos = np.vstack(copias).astype(np.float32)
    datos /= np.linalg.norm(datos, axis=1, keepdims=True)
    n = len(datos)
    ids = [f"r{i:06d}" for i in range(n)]
    fila = {"registros": n}

    # pgvector
    inicio = time.perf_counter()
    cur.execute(f"DROP TABLE IF EXISTS {ESCALA};")
    cur.execute(f"CREATE TABLE {ESCALA} (id VARCHAR(20) PRIMARY KEY, contenido TEXT, vector vector(384));")
    execute_values(cur, f"INSERT INTO {ESCALA} (id, contenido, vector) VALUES %s",
                   [(i, "", v) for i, v in zip(ids, datos)], page_size=1000)
    cur.execute(f"CREATE INDEX ON {ESCALA} USING hnsw (vector vector_cosine_ops);")
    pg.commit()
    carga = time.perf_counter() - inicio
    t = medir(lambda: buscar_pg(vectores_preg[0], 5, tabla=ESCALA))
    fila["PostgreSQL (pgvector)"] = {"carga_s": round(carga, 2), **t}
    print(f"{n:>10,} | {'PostgreSQL (pgvector)':24} | {carga:9.2f} | {t['promedio_ms']:19.2f}")

    # ChromaDB
    inicio = time.perf_counter()
    try:
        chroma.delete_collection(ESCALA)
    except Exception:
        pass
    col = chroma.create_collection(ESCALA, metadata={"hnsw:space": "cosine"})
    for a in range(0, n, 2000):
        col.add(ids=ids[a:a + 2000], embeddings=datos[a:a + 2000].tolist(), documents=[""] * len(ids[a:a + 2000]))
    carga = time.perf_counter() - inicio
    t = medir(lambda: buscar_chroma(vectores_preg[0], 5, col=col))
    fila["ChromaDB"] = {"carga_s": round(carga, 2), **t}
    print(f"{n:>10,} | {'ChromaDB':24} | {carga:9.2f} | {t['promedio_ms']:19.2f}")

    # Qdrant
    inicio = time.perf_counter()
    if qdrant.collection_exists(ESCALA):
        qdrant.delete_collection(ESCALA)
    qdrant.create_collection(ESCALA, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
    for a in range(0, n, 1000):
        qdrant.upsert(ESCALA, points=[PointStruct(id=a + j, vector=v.tolist(), payload={"id": ids[a + j]})
                                      for j, v in enumerate(datos[a:a + 1000])], wait=True)
    carga = time.perf_counter() - inicio
    t = medir(lambda: buscar_qdrant(vectores_preg[0], 5, col=ESCALA))
    fila["Qdrant"] = {"carga_s": round(carga, 2), **t}
    print(f"{n:>10,} | {'Qdrant':24} | {carga:9.2f} | {t['promedio_ms']:19.2f}")
    resultados["escalabilidad"].append(fila)

# Limpieza de las estructuras temporales
cur.execute(f"DROP TABLE IF EXISTS {ESCALA};")
pg.commit()
chroma.delete_collection(ESCALA)
qdrant.delete_collection(ESCALA)
pg.close()

Path("resultados/evaluacion.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nResultados guardados en resultados/evaluacion.json")