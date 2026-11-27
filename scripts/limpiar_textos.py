

import re
from pathlib import Path

# Carpetas del proyecto
carpeta_entrada = Path("datos_procesados")
carpeta_salida = Path("datos_procesados/limpios")

carpeta_salida.mkdir(parents=True, exist_ok=True)

archivos_txt = list(carpeta_entrada.glob("*.txt"))

print("Archivos encontrados:", len(archivos_txt))


def limpiar_texto(texto, nombre_documento):

    lineas = texto.splitlines()
    lineas_limpias = []

    i = 0

    while i < len(lineas):

        linea = lineas[i].strip()
        linea_normalizada = re.sub(r"\s+", "", linea).casefold()

        # Eliminar pie de página del Manual
        if nombre_documento == "Manual de Procedimientos Académicos UNAH":

            if re.fullmatch(
                r"manualdeprocedimientosacadémicosdelaunah\|\d+",
                linea_normalizada
            ):
                i += 1
                continue

        # Eliminar pie de página de Normas Académicas
        if nombre_documento == "Normas-Academica-de-la-UNAH":

            encabezado = (
                "normasacadémicasdelauniversidadnacional"
                "autónomadehonduras"
            )

            if linea_normalizada == encabezado:
                i += 1

                # Eliminar el número de página que sigue al encabezado
                if i < len(lineas) and re.fullmatch(
                    r"\s*\d+\s*", lineas[i]
                ):
                    i += 1

                continue

        # Eliminar pies de página del Reglamento
        if nombre_documento == "Reglamento-de-los-Estudiantes-de-la-UNAH-Comisionado-Universitario":

            if linea_normalizada in [
                "digitalizadoporudi-cra-unah",
                "derechosreservados"
            ]:
                i += 1
                continue

            # Eliminar texto defectuoso del pie de página
            if re.fullmatch(r"a{6,}", linea_normalizada):
                i += 1
                continue

        if linea:
            lineas_limpias.append(linea)

        i += 1

    texto = "\n".join(lineas_limpias)

    # Reducir espacios repetidos
    texto = re.sub(r"[ \t]+", " ", texto)

    # Reducir saltos de línea excesivos
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


# Procesar documentos
for archivo in archivos_txt:

    print("\nLimpiando:", archivo.name)

    texto = archivo.read_text(encoding="utf-8")

    texto_limpio = limpiar_texto(texto, archivo.stem)

    ruta_salida = carpeta_salida / archivo.name

    ruta_salida.write_text(
        texto_limpio,
        encoding="utf-8"
    )

    print("Caracteres originales:", len(texto))
    print("Caracteres limpios:", len(texto_limpio))
    print("Archivo guardado:", ruta_salida)

print("\nLimpieza de documentos finalizada.")


