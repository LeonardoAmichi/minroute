import json
import subprocess
import sys
import os
from pathlib import Path

"""
Este arquivo serve como uma "ponte" de comunicação entre o nosso programa (em Python) 
e a inteligência de cálculo de rotas (escrita em Java). 
Como o Java é mais rápido para as matemáticas complexas do algoritmo, 
mandamos o mapa para ele e pegamos o resultado de volta!
"""

def run_dijkstra(java_cp: Path, snapshot_path: Path, origem: int, destino: int) -> dict:
    """
    Chama o programa Java, passa o mapa atualizado e pede a melhor rota entre dois pontos.
    """
    # Descobre onde está instalado o Java (JRE) dentro da nossa pasta, para funcionar em qualquer PC
    if getattr(sys, 'frozen', False):
        java_exe = Path(sys._MEIPASS) / "jre" / "bin" / "java.exe"
    else:
        local_jre = Path(__file__).resolve().parents[2] / "jre" / "bin" / "java.exe"
        java_exe = local_jre if local_jre.exists() else "java"

    # Monta a frase (comando) que vamos mandar para o terminal
    comando = [
        str(java_exe),
        "-client",               # Inicia o Java de forma mais rápida
        "-cp",                   # Diz onde estão os códigos Java compilados
        str(java_cp),
        "src.core.DijkstraCore", # Nome da classe Java principal
        str(snapshot_path),      # Caminho do mapa atual (que o Java vai ler)
        str(origem),             # Ponto de saída
        str(destino),            # Ponto de chegada
    ]

    # No Windows, usamos esse truque para esconder a tela preta do terminal
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    try:
        # Executa o comando de fato e aguarda a resposta (capture_output=True)
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True, **kwargs)
        # O Java nos responde em formato JSON, então traduzimos isso para um dicionário Python
        return json.loads(resultado.stdout)
    except subprocess.CalledProcessError as e:
        # Tenta interpretar a mensagem de erro formatada como JSON para exibir algo amigável
        if e.stderr:
            try:
                erro_json = json.loads(e.stderr)
                if "erro" in erro_json:
                    raise RuntimeError(erro_json["erro"])
            except json.JSONDecodeError:
                pass
        
        # Se falhou ou não era JSON, mostramos a mensagem que tiver
        mensagem = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(mensagem)
