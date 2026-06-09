import json
import subprocess
import sys
import os
from pathlib import Path


def run_dijkstra(java_cp: Path, snapshot_path: Path, origem: int, destino: int) -> dict:
    if getattr(sys, 'frozen', False):
        java_exe = Path(sys._MEIPASS) / "jre" / "bin" / "java.exe"
    else:
        local_jre = Path(__file__).resolve().parents[2] / "jre" / "bin" / "java.exe"
        java_exe = local_jre if local_jre.exists() else "java"

    comando = [
        str(java_exe),
        "-client",
        "-cp",
        str(java_cp),
        "src.core.DijkstraCore",
        str(snapshot_path),
        str(origem),
        str(destino),
    ]

    # Esconde a janela do console do Java no Windows
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True, **kwargs)
        return json.loads(resultado.stdout)
    except subprocess.CalledProcessError as e:
        mensagem = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(mensagem)

