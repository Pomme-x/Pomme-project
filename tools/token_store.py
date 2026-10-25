# -*- coding: utf-8 -*-
"""Windows DPAPI 加密保存 GitHub Token。

只有当前 Windows 用户能解密；文件放在 %APPDATA%\\Pomme\\token.bin。
"""

import base64
import ctypes
import ctypes.wintypes as wt
import os
from pathlib import Path

TOKEN_FILE = Path(os.environ.get('APPDATA', str(Path.home()))) / 'Pomme' / 'token.bin'
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', wt.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _make_blob(data: bytes):
    buf = ctypes.create_string_buffer(data, len(data))
    blob = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    return blob, buf


def _protect(data: bytes) -> bytes:
    blob_in, _keep = _make_blob(data)
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), 'pomme', None, None, None,
        CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not ok:
        raise OSError('CryptProtectData failed')
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _unprotect(data: bytes) -> bytes:
    blob_in, _keep = _make_blob(data)
    blob_out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None,
        CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not ok:
        raise OSError('CryptUnprotectData failed')
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def save_token(token: str):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_bytes(base64.b64encode(_protect(token.encode('utf-8'))))


def load_token():
    try:
        raw = TOKEN_FILE.read_bytes()
    except FileNotFoundError:
        return None
    try:
        return _unprotect(base64.b64decode(raw)).decode('utf-8')
    except Exception:
        return None


def clear_token():
    try:
        TOKEN_FILE.unlink()
    except FileNotFoundError:
        pass
