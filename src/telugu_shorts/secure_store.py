"""Windows DPAPI storage for OAuth refresh tokens (no third-party package)."""
import ctypes
import os
from ctypes import wintypes
from pathlib import Path


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _protect(data, decrypt=False):
    if os.name != "nt":
        raise OSError("OAuth token storage currently requires Windows DPAPI")
    raw = bytes(data)
    source_buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
    source = DATA_BLOB(len(raw), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    destination = DATA_BLOB()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    if decrypt:
        fn = crypt.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.POINTER(DATA_BLOB),
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        ok = fn(ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(destination))
    else:
        fn = crypt.CryptProtectData
        fn.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB),
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        ok = fn(ctypes.byref(source), "Telugu Devotional Shorts OAuth", None, None, None, 0x1,
                ctypes.byref(destination))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel.LocalFree(destination.pbData)


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_protect(data))


def load(path):
    return _protect(Path(path).read_bytes(), decrypt=True)
