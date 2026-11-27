import pymupdf
import pytesseract
from PIL import Image
from pathlib import Path
from io import BytesIO

# Configuración de Tesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Carpetas
carpeta_documentos = Path("documentos_originales")
carpeta_salida = Path("datos_procesados")
carpeta_salida.mkdir(exist_ok=True)

# Buscar los tres PDF
archivos_pdf = list(carpeta_documentos.glob("*.pdf"))

print("Documentos encontrados:", len(archivos_pdf))

# Páginas que se excluirán de la extracción
paginas_omitidas = {
    "Manual de Procedimientos Académicos UNAH": [1, 2, 3, 4, 7],
    "Normas-Academica-de-la-UNAH": list(range(1, 14)) + [107, 108, 109, 110],
    "Reglamento-de-los-Estudiantes-de-la-UNAH-Comisionado-Universitario": [2]
}

for archivo in archivos_pdf:

    print("\nProcesando:", archivo.name)

    documento = pymupdf.open(archivo)
    texto_completo = ""

    for numero, pagina in enumerate(documento, start=1):

        # Saltar páginas que no contienen información útil
        if numero in paginas_omitidas.get(archivo.stem, []):
            print(f"Página {numero} omitida.")
            continue

        # Intentar extraer texto directamente
        texto = pagina.get_text().strip()

        # Si la página no tiene texto suficiente, aplicar OCR
        if len(texto) < 100:

            print(f"Aplicando OCR a la página {numero}...")

            pix = pagina.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False
            )

            imagen = Image.open(BytesIO(pix.tobytes("png")))

            texto = pytesseract.image_to_string(
                imagen,
                lang="spa"
            )

        # Guardar texto y número de página
        texto_completo += (
            f"\n--- Página {numero} ---\n"
            + texto
            + "\n"
        )

    documento.close()

    # Crear archivo TXT con el nombre del PDF
    nombre_salida = archivo.stem + ".txt"
    ruta_salida = carpeta_salida / nombre_salida

    ruta_salida.write_text(
        texto_completo,
        encoding="utf-8"
    )

    print("Páginas procesadas:", numero)
    print("Caracteres extraídos:", len(texto_completo))
    print("Archivo guardado:", ruta_salida)

print("\nExtracción de todos los documentos finalizada.")


