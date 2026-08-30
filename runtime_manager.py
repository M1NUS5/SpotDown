"""
Gestiona un entorno Python independiente para spotDL/yt-dlp.

Por qué existe este módulo:
Cuando SpotDown se empaqueta como app de macOS, spotDL y yt-dlp
quedaban "congelados" dentro del ejecutable. YouTube cambia con
frecuencia la forma en que protege sus streams, y cuando eso pasa,
yt-dlp necesita actualizarse para seguir funcionando. Una versión
congelada dentro de un .app no puede actualizarse sola.

Este módulo crea (la primera vez) un entorno virtual de Python en la
carpeta de datos del usuario y, de ahí en adelante, revisa
periódicamente si hay una versión más nueva de spotDL/yt-dlp y la
instala automáticamente, sin necesidad de reconstruir ni reinstalar
la app.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path


NOMBRE_APP = "SpotDown"
PAQUETES_GESTIONADOS = ["spotdl", "yt-dlp"]

# No molestamos al usuario revisando actualizaciones en cada arranque:
# solo lo hacemos si ya pasaron este tiempo desde la última revisión.
INTERVALO_ACTUALIZACION_HORAS = 24


def directorio_datos_app() -> Path:
    """
    Carpeta persistente propia de SpotDown, fuera del .app,
    donde vive el entorno Python gestionado.
    """
    sistema = platform.system()

    if sistema == "Darwin":
        base = Path.home() / "Library" / "Application Support" / NOMBRE_APP
    elif sistema == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home())) / NOMBRE_APP
    else:
        base = Path.home() / ".local" / "share" / NOMBRE_APP

    base.mkdir(parents=True, exist_ok=True)
    return base


def _ruta_entorno() -> Path:
    return directorio_datos_app() / "runtime"


def _ruta_marca_tiempo() -> Path:
    return directorio_datos_app() / "ultima_actualizacion.json"


def _python_del_entorno() -> Path:
    entorno = _ruta_entorno()

    if platform.system() == "Windows":
        return entorno / "Scripts" / "python.exe"

    return entorno / "bin" / "python"


def entorno_listo() -> bool:
    return _python_del_entorno().exists()


def _buscar_python_sistema() -> str | None:
    """
    Busca un intérprete de Python 3 utilizable en el sistema
    para crear el entorno virtual la primera vez.
    """
    candidatos = ["python3", "python"]

    for nombre in candidatos:
        ruta = shutil.which(nombre)

        if ruta is None:
            continue

        try:
            resultado = subprocess.run(
                [ruta, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            salida = (resultado.stdout + resultado.stderr).strip()

            if "Python 3" in salida:
                return ruta

        except Exception:
            continue

    # Rutas típicas en macOS cuando no está en PATH todavía.
    rutas_macos = [
        "/usr/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
    ]

    for ruta in rutas_macos:
        if Path(ruta).exists():
            return ruta

    return None


def _leer_marca_tiempo() -> float:
    ruta = _ruta_marca_tiempo()

    if not ruta.exists():
        return 0.0

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            return float(datos.get("ultima_revision", 0.0))

    except (json.JSONDecodeError, OSError, ValueError):
        return 0.0


def _guardar_marca_tiempo() -> None:
    try:
        with open(_ruta_marca_tiempo(), "w", encoding="utf-8") as archivo:
            json.dump({"ultima_revision": time.time()}, archivo)

    except OSError:
        pass


def _necesita_revision(forzar: bool) -> bool:
    if forzar:
        return True

    ultima = _leer_marca_tiempo()
    horas_transcurridas = (time.time() - ultima) / 3600
    return horas_transcurridas >= INTERVALO_ACTUALIZACION_HORAS


def crear_entorno(mostrar_estado: Callable[[str], None]) -> bool:
    """
    Crea el entorno virtual por primera vez e instala spotDL/yt-dlp.
    Devuelve True si el entorno quedó listo para usarse.
    """
    python_sistema = _buscar_python_sistema()

    if python_sistema is None:
        mostrar_estado(
            "No se encontró Python 3 en el sistema. "
            "Instálalo desde python.org y vuelve a abrir SpotDown."
        )
        return False

    mostrar_estado("Preparando SpotDown por primera vez...")

    try:
        subprocess.run(
            [python_sistema, "-m", "venv", str(_ruta_entorno())],
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )

    except Exception as error:
        mostrar_estado(f"No se pudo crear el entorno: {error}")
        return False

    return _instalar_o_actualizar_paquetes(mostrar_estado)


def _instalar_o_actualizar_paquetes(
    mostrar_estado: Callable[[str], None]
) -> bool:
    python_entorno = _python_del_entorno()

    if not python_entorno.exists():
        return False

    try:
        subprocess.run(
            [
                str(python_entorno),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        resultado = subprocess.run(
            [
                str(python_entorno),
                "-m",
                "pip",
                "install",
                "--upgrade",
                *PAQUETES_GESTIONADOS,
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False
        )

        if resultado.returncode != 0:
            mostrar_estado(
                "No se pudieron actualizar spotDL/yt-dlp "
                "(sin conexión o error temporal). "
                "Se usará la última versión instalada."
            )
            # No es un error fatal: seguimos con lo que ya haya instalado.
            return _python_del_entorno().exists()

        _guardar_marca_tiempo()
        return True

    except subprocess.TimeoutExpired:
        mostrar_estado(
            "La actualización tardó demasiado, se usará "
            "la última versión instalada."
        )
        return _python_del_entorno().exists()

    except Exception as error:
        mostrar_estado(f"Error al actualizar dependencias: {error}")
        return _python_del_entorno().exists()


def asegurar_entorno(
    mostrar_estado: Callable[[str], None],
    forzar_actualizacion: bool = False
) -> bool:
    """
    Punto de entrada principal: garantiza que exista un entorno
    con spotDL/yt-dlp listo para usarse, y lo actualiza en segundo
    plano si ya pasó el intervalo configurado (o si se fuerza).

    Se debe llamar al iniciar la app, antes de permitir descargas.
    """
    if not entorno_listo():
        return crear_entorno(mostrar_estado)

    if _necesita_revision(forzar_actualizacion):
        mostrar_estado("Revisando actualizaciones de spotDL/yt-dlp...")
        return _instalar_o_actualizar_paquetes(mostrar_estado)

    return True


def python_para_descargas() -> str:
    """
    Ruta del intérprete a usar para invocar spotDL.
    Si el entorno gestionado existe, se usa ese; si no, se recurre
    al intérprete que esté ejecutando la app (modo desarrollo).
    """
    python_entorno = _python_del_entorno()

    if python_entorno.exists():
        return str(python_entorno)

    return sys.executable
