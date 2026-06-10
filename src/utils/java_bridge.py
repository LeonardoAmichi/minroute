import json
import subprocess
import sys
import os
from pathlib import Path

"""
Ponte entre a aplicação Python e o motor de cálculo escrito em Java.
Encapsula a invocação do processo Java e a conversão do JSON retornado.
"""

def run_dijkstra(java_cp: Path, snapshot_path: Path, origem: int, destino: int) -> dict:
    """
    Chama o programa Java, passa o mapa atualizado e pede a melhor rota entre dois pontos.
    """
    # Detecta um executável Java empacotado ou usa o 'java' do sistema
    if getattr(sys, 'frozen', False):
        java_exe = Path(sys._MEIPASS) / "jre" / "bin" / "java.exe"
    else:
        local_jre = Path(__file__).resolve().parents[2] / "jre" / "bin" / "java.exe"
        java_exe = local_jre if local_jre.exists() else "java"

    # Monta o comando para executar a classe Java responsável pelo Dijkstra
    comando = [
        str(java_exe),
        "-client",               # Flag para iniciar JVM em modo cliente (quando aplicável)
        "-cp",                   # Classpath: diretório com classes compiladas
        str(java_cp),
        "src.core.DijkstraCore", # Nome da classe Java principal
        str(snapshot_path),      # Caminho do mapa atual (que o Java vai ler)
        str(origem),             # Ponto de saída
        str(destino),            # Ponto de chegada
    ]

    # Em Windows, evita exibir janela de console ao executar o processo
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    try:
        # Executa o processo e captura a saída padrão (espera JSON do Java)
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True, **kwargs)
        # Converte JSON retornado pelo Java em dicionário Python
        return json.loads(resultado.stdout)
    except subprocess.CalledProcessError as e:
        # Tenta interpretar stderr como JSON para extrair mensagem de erro amigável
        if e.stderr:
            try:
                erro_json = json.loads(e.stderr)
                if "erro" in erro_json:
                    raise RuntimeError(erro_json["erro"])
            except json.JSONDecodeError:
                pass
        
        # Caso contrário, propaga mensagem de erro genérica
        mensagem = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(mensagem)
