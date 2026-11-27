

from pathlib import Path
import json

# Carpetas
carpeta_entrada = Path("datos_procesados/limpios")
carpeta_salida = Path("datos_procesados")

# Parámetros de fragmentación
TAMANO_FRAGMENTO = 1000
SOLAPAMIENTO = 150
TAMANO_MINIMO = 700
TAMANO_MAXIMO = 1200


def buscar_corte(texto, inicio):

    limite = min(inicio + TAMANO_FRAGMENTO, len(texto))
    minimo = inicio + TAMANO_MINIMO
    maximo = min(inicio + TAMANO_MAXIMO, len(texto))

    if maximo >= len(texto):
        return len(texto)

    # Buscar primero el final de un párrafo
    corte = texto.rfind("\n\n", minimo, maximo)

    if corte != -1:
        return corte

    # Si no hay párrafo, buscar el final de una oración
    for separador in [". ", "? ", "! ", ": "]:

        corte = texto.rfind(separador, minimo, maximo)

        if corte != -1:
            return corte + 1

    # Si no hay oración, buscar el último espacio
    corte = texto.rfind(" ", inicio, limite)

    if corte != -1:
        return corte

    # Último recurso
    corte = texto.find(" ", limite)

    if corte != -1:
        return corte

    return len(texto)


# Buscar documentos
archivos_txt = list(carpeta_entrada.glob("*.txt"))

fragmentos = []
contador = 1

print("Documentos encontrados:", len(archivos_txt))

# Procesar cada documento
for archivo in archivos_txt:

    print("\nFragmentando:", archivo.name)

    texto = archivo.read_text(encoding="utf-8")

    inicio = 0
    indice_fragmento = 0

    while inicio < len(texto):

        fin = buscar_corte(texto, inicio)

        contenido = texto[inicio:fin].strip()

        if contenido:

            fragmento = {
                "id": f"chunk_{contador:04d}",
                "contenido": contenido,
                "documento": archivo.stem,
                "categoria": "Documentos académicos UNAH",
                "fuente": archivo.name,
                "indice_fragmento": indice_fragmento
            }

            fragmentos.append(fragmento)

            contador += 1
            indice_fragmento += 1

        if fin >= len(texto):
            break

        # Preparar el siguiente fragmento con solapamiento
        nuevo_inicio = max(inicio + 1, fin - SOLAPAMIENTO)

        # Evitar comenzar en medio de una palabra
        while nuevo_inicio < len(texto) and not texto[nuevo_inicio].isspace():
            nuevo_inicio += 1

        inicio = nuevo_inicio

    print("Fragmentos generados:", indice_fragmento)

# Guardar todos los fragmentos en JSON
archivo_salida = carpeta_salida / "fragmentos.json"

with open(archivo_salida, "w", encoding="utf-8") as archivo:

    json.dump(
        fragmentos,
        archivo,
        ensure_ascii=False,
        indent=4
    )

print("\nFragmentación finalizada.")
print("Total de fragmentos:", len(fragmentos))
print("Archivo generado:", archivo_salida)

