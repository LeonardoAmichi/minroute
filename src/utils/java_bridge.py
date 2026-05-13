import json
import subprocess
from pathlib import Path


def run_dijkstra(java_cp: Path, snapshot_path: Path, origem: int, destino: int) -> dict:
    comando = [
        "java",
        "-cp",
        str(java_cp),
        "src.core.DijkstraCore",
        str(snapshot_path),
        str(origem),
        str(destino),
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
    return json.loads(resultado.stdout)
