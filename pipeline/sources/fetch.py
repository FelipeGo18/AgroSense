"""Descargas con límites: tiempo total y tamaño máximo (docs/revision-de-pr.md, «Seguridad»).

`urlopen(timeout=…)` cuenta el tiempo de cada lectura del socket, no el de toda la descarga: una conexión que manda un
byte cada pocos minutos nunca terminaría. Aquí se corta al pasar el tiempo total o el tamaño, y solo queda el archivo
completo: lo que se bajaba se borra (R1).
"""

import http.client
import time
import urllib.request
from pathlib import Path

CHUNK = 1 << 20


class DownloadError(OSError):
    """Una descarga se cortó: por tiempo, por tamaño o porque el servidor cerró la conexión a mitad. Es un `OSError`
    como los demás cortes de red: se reintenta igual."""


def fetch(request: urllib.request.Request, dest: Path, timeout_s: float, max_bytes: int) -> Path:
    """Baja `request` a `dest` por partes. Corta si pasa de `max_bytes` o de `timeout_s` segundos de punta a punta.

    TLS se verifica (el contexto por defecto de `urllib`). Los errores HTTP (`HTTPError`, por ejemplo un 404) y de red
    pasan tal cual a quien llama. Un corte a mitad de la respuesta (`IncompleteRead`, que no es un `OSError`) sale como
    `DownloadError`, para que se reintente como los demás cortes de red.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    deadline = time.monotonic() + timeout_s
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response, partial.open("wb") as out:  # noqa: S310
            size = 0
            while chunk := response.read(CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise DownloadError(f"la respuesta pasó de {max_bytes / 2**20:.0f} MB")
                if time.monotonic() > deadline:
                    raise DownloadError(f"la descarga pasó de {timeout_s:.0f} s")
                out.write(chunk)
        partial.replace(dest)
    except http.client.HTTPException as error:
        raise DownloadError(f"la conexión se cortó a mitad de la respuesta ({type(error).__name__})") from error
    finally:
        partial.unlink(missing_ok=True)
    return dest
