import ctypes
import platform
import subprocess


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

proceso_caffeinate = None


def evitar_suspension():
    global proceso_caffeinate

    sistema = platform.system()

    # Windows
    if sistema == "Windows":
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )

    # macOS
    elif sistema == "Darwin":
        if proceso_caffeinate is None:
            proceso_caffeinate = subprocess.Popen(
                ["caffeinate", "-i"]
            )


def permitir_suspension():
    global proceso_caffeinate

    sistema = platform.system()

    # Windows
    if sistema == "Windows":
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS
        )

    # macOS
    elif sistema == "Darwin":
        if proceso_caffeinate is not None:
            proceso_caffeinate.terminate()
            proceso_caffeinate.wait()
            proceso_caffeinate = None