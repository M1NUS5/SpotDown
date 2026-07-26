import json
import os

ARCHIVO_CONFIG = "config.json"


def cargar_configuracion():
    if not os.path.exists(ARCHIVO_CONFIG):
        return {
            "carpeta": ""
        }

    try:
        with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    except (json.JSONDecodeError, OSError):
        return {
            "carpeta": ""
        }


def guardar_configuracion(carpeta):
    datos = {
        "carpeta": carpeta
    }

    try:
        with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as archivo:
            json.dump(
                datos,
                archivo,
                indent=4,
                ensure_ascii=False
            )

    except OSError as error:
        print(f"No se pudo guardar la configuración: {error}")