

import re
from pathlib import Path

carpeta = Path("datos_procesados/limpios")

for archivo in carpeta.glob("*.txt"):

    print("\n" + "=" * 60)
    print("DOCUMENTO:", archivo.name)
    print("=" * 60)

    texto = archivo.read_text(encoding="utf-8")
    encontradas = 0

    for numero, linea in enumerate(texto.splitlines(), start=1):

        # Detectar líneas con varias letras individuales separadas
        palabras = re.findall(
            r"\b(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\s+){3,}[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\b",
            linea
        )

        if palabras:
            print(f"\nLínea {numero}:")
            print(linea[:300])
            encontradas += 1

        if encontradas >= 10:
            print("\nSe muestran solamente 10 coincidencias.")
            break

    if encontradas == 0:
        print("No se encontraron coincidencias.")
