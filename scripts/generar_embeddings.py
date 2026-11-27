

from sentence_transformers import SentenceTransformer
from pathlib import Path
import json
import numpy as np

# Rutas del proyecto
ruta_fragmentos = Path("datos_procesados/fragmentos.json")
ruta_embeddings = Path("datos_procesados/embeddings.npy")
ruta_info = Path("datos_procesados/embeddings_info.json")

print("Cargando fragmentos...")

with open(ruta_fragmentos, "r", encoding="utf-8") as archivo:
    fragmentos = json.load(archivo)

print("Fragmentos encontrados:", len(fragmentos))

# Cargar modelo
print("\nCargando modelo de embeddings...")

modelo = SentenceTransformer("intfloat/multilingual-e5-small")

# Preparar textos
textos = [
    "passage: " + fragmento["contenido"]
    for fragmento in fragmentos
]

print("\nGenerando embeddings...")

embeddings = modelo.encode(
    textos,
    batch_size=32,
    show_progress_bar=True,
    normalize_embeddings=True
)

# Guardar matriz de vectores
np.save(ruta_embeddings, embeddings)

# Guardar información asociada a los vectores
with open(ruta_info, "w", encoding="utf-8") as archivo:
    json.dump(
        fragmentos,
        archivo,
        ensure_ascii=False,
        indent=4
    )

print("\nGeneración finalizada.")
print("Cantidad de vectores:", embeddings.shape[0])
print("Dimensiones por vector:", embeddings.shape[1])
print("Archivo de vectores:", ruta_embeddings)
print("Archivo de información:", ruta_info)
