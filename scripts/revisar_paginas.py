
import pymupdf
import pytesseract
from PIL import Image
from pathlib import Path
import io

# Ubicación de Tesseract en Windows
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

carpeta_pdf = Path("documentos_originales")
carpeta_resultados = Path("resultados")

carpeta_resultados.mkdir(exist_ok=True)

archivos_pdf = list(carpeta_pdf.glob("*.pdf"))

salida = []

for archivo in archivos_pdf:

    print(f"\nRevisando: {archivo.name}")

    documento = pymupdf.open(archivo)

    salida.append("=" * 80)
    salida.append(f"DOCUMENTO: {archivo.name}")
    salida.append(f"TOTAL DE PAGINAS: {len(documento)}")
    salida.append("=" * 80)

    for numero, pagina in enumerate(documento, start=1):

        texto = pagina.get_text().strip()

        # Si la página tiene poco texto, intentamos OCR
        if len(texto) < 100:

            pix = pagina.get_pixmap(dpi=200)
            imagen = Image.open(io.BytesIO(pix.tobytes("png")))

            texto = pytesseract.image_to_string(
                imagen,
                lang="spa"
            )

        # Resumen de la página
        texto = " ".join(texto.split())

        resumen = texto[:500]

        salida.append(f"\n--- PAGINA {numero} ---")
        salida.append(resumen if resumen else "[Página sin texto]")

        print(f"Página {numero} revisada")

    documento.close()

# Guardar todo en un archivo
archivo_salida = carpeta_resultados / "revision_paginas.txt"

with open(archivo_salida, "w", encoding="utf-8") as f:
    f.write("\n".join(salida))

print("\n========================================")
print("REVISION FINALIZADA")
print("Archivo generado:", archivo_salida)
print("========================================")