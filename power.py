import ctypes

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def evitar_suspension():
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )


def permitir_suspension():
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS
    )