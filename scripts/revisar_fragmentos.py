

import json
from pathlib import Path

# Ubicación del archivo de fragmentos
ruta_archivo = Path("datos_procesados/fragmentos.json")

# Verificar que exista el archivo
if not ruta_archivo.exists():
    print("ERROR: No se encontró fragmentos.json")
    exit()

# Cargar los fragmentos
with open(ruta_archivo, "r", encoding="utf-8") as archivo:
    fragmentos = json.load(archivo)

print("=" * 50)
print("REVISION DE FRAGMENTOS")
print("=" * 50)

# Cantidad de fragmentos
print("\nTotal de fragmentos:", len(fragmentos))

# Verificar identificadores únicos
ids = [fragmento.get("id") for fragmento in fragmentos]
ids_unicos = set(ids)

print("Identificadores únicos:", len(ids_unicos))

if len(ids) == len(ids_unicos):
    print("Correcto: no hay identificadores repetidos.")
else:
    print("ERROR: existen identificadores repetidos.")

# Campos obligatorios
campos = ["id", "contenido", "documento", "categoria", "fuente"]

errores = 0

for numero, fragmento in enumerate(fragmentos, start=1):

    for campo in campos:

        if campo not in fragmento or not fragmento[campo]:
            print(f"Falta el campo '{campo}' en el fragmento {numero}.")
            errores += 1

# Verificar contenido vacío
vacios = [
    fragmento for fragmento in fragmentos
    if not fragmento.get("contenido", "").strip()
]

print("\nFragmentos sin contenido:", len(vacios))
print("Errores de campos obligatorios:", errores)

# Mostrar cinco ejemplos
print("\n" + "=" * 50)
print("EJEMPLOS DE FRAGMENTOS")
print("=" * 50)

for fragmento in fragmentos[:5]:

    print("\nID:", fragmento.get("id"))
    print("Documento:", fragmento.get("documento"))
    print("Categoría:", fragmento.get("categoria"))
    print("Fuente:", fragmento.get("fuente"))
    print("Contenido:", fragmento.get("contenido", "")[:200])
    print("-" * 50)

# Resultado final
print("\n" + "=" * 50)

if errores == 0 and len(ids) == len(ids_unicos) and len(vacios) == 0:
    print("RESULTADO: TODOS LOS FRAGMENTOS PASARON LA REVISION.")
else:
    print("RESULTADO: SE ENCONTRARON PROBLEMAS QUE DEBEMOS REVISAR.")

if len(fragmentos) >= 500:
    print("REQUISITO DE 500 FRAGMENTOS: CUMPLIDO.")
else:
    print("REQUISITO DE 500 FRAGMENTOS: NO CUMPLIDO.")

print("=" * 50)
