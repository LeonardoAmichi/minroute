from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
import math

# Tipos auxiliares para clareza de código
VertexId = int
Point = Tuple[float, float]
Edge = Tuple[int, int, bool]


def load_txt(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Carrega um grafo a partir de um arquivo TXT simples.
    Ignora comentários (linhas iniciadas por '#') e interpreta cabeçalho e seções.
    """
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []

    with path.open("r", encoding="utf-8") as f:
        # Lê linhas não vazias, removendo espaços e filtrando comentários
        linhas = [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]
        if not linhas:
            return {}, []
            
        partes_cabecalho = linhas[0].split()
        if len(partes_cabecalho) < 2:
            return {}, []
            
        n = int(partes_cabecalho[0]) # Total de vértices
        m = int(partes_cabecalho[1]) # Total de arestas
        
        idx = 1
        # Lendo as posições de cada ponto (vértice)
        for _ in range(n):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 3:
                id_no = int(partes[0])
                    # Normaliza o separador decimal (vírgula -> ponto)
                x = float(partes[1].replace(",", "."))
                y = float(partes[2].replace(",", "."))
                vertices[id_no] = (x, y)
            idx += 1
            
        # Lê as definições de arestas que conectam vértices
        for _ in range(m):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 2:
                u = int(partes[0])
                v = int(partes[1])
                is_bidirectional = True
                # A terceira coluna, se presente, indica direção (0 = bidirecional)
                if len(partes) >= 3:
                    is_bidirectional = (int(partes[2]) == 0)
                edges.append((u, v, is_bidirectional))
            idx += 1

    return vertices, edges


def load_poly(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Lê arquivos .poly e converte em estruturas de vértices e arestas.
    """
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []

    with path.open("r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]
        if not linhas:
            return {}, []
            
        idx = 0
        total_vertices = int(linhas[idx].split()[0])
        idx += 1
        
        # Lê coordenadas X e Y de cada vértice
        for _ in range(total_vertices):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            id_no = int(partes[0])
            x = float(partes[1].replace(",", "."))
            y = float(partes[2].replace(",", "."))
            vertices[id_no] = (x, y)
            idx += 1
            
        if idx >= len(linhas): return vertices, edges
        
        total_arestas = int(linhas[idx].split()[0])
        idx += 1
        
        # Lê definições das arestas (origem, destino e direção)
        for _ in range(total_arestas):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 3:
                u = int(partes[1])
                v = int(partes[2])
                is_bidirectional = True
                # Interpreta a flag de direção, quando presente
                if len(partes) >= 4:
                    is_bidirectional = (int(partes[3]) == 0)
                edges.append((u, v, is_bidirectional))
            idx += 1

    return vertices, edges


def load_osm(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Parser para arquivos OSM: converte nós e ways em vértices e arestas,
    aplicando projeção Mercator simplificada para coordenadas planas.
    """
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []
    
    # Raio da Terra (metros) utilizado na projeção
    RAIO_TERRA = 6378137.0

    # Parsing iterativo do XML para reduzir uso de memória
    context = ET.iterparse(path, events=('end',))
    
    vertices_temp = {}
    vias_temp = []
    
    # 1. Lê sequencialmente o arquivo, liberando a memória do que já foi processado
    for event, elem in context:
        if elem.tag == 'node':
            id_str = elem.get('id')
            lat_str = elem.get('lat')
            lon_str = elem.get('lon')
            if id_str and lat_str and lon_str:
                id_no = int(id_str)
                lat = float(lat_str)
                lon = float(lon_str)
                
                # Converte latitude/longitude para projeção plana (Mercator)
                x = RAIO_TERRA * math.radians(lon)
                y = RAIO_TERRA * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
                
                vertices_temp[id_no] = (x, y)
            # Libera elementos processados para manter uso de memória baixo
            elem.clear()
            
        elif elem.tag == 'way':
            nds = elem.findall('nd')
            via = []
            for nd in nds:
                ref_str = nd.get('ref')
                if ref_str:
                    ref = int(ref_str)
                    if ref in vertices_temp:
                        via.append(ref)
                        
            # Determina o valor 'oneway' a partir das tags da via
            oneway_val = 0
            for tag in elem.findall('tag'):
                if tag.get('k') == 'oneway':
                    v = tag.get('v')
                    if v in ('yes', 'true', '1'):
                        oneway_val = 1
                    elif v in ('-1', 'reverse'):
                        oneway_val = -1
            
            if len(via) > 1:
                vias_temp.append((via, oneway_val))
            # Libera elemento da via
            elem.clear()

    # Normaliza IDs OSM para um índice inteiro sequencial (0..N-1)
    mapa_ids = {}
    novo_id = 0
    for old_id, point in vertices_temp.items():
        mapa_ids[old_id] = novo_id
        vertices[novo_id] = point
        novo_id += 1
        
    # Conecta nós em arestas seguindo a ordem das vias e regras de direção
    for via, oneway_val in vias_temp:
        for i in range(len(via) - 1):
            from_orig = via[i]
            to_orig = via[i+1]
            
            from_int = mapa_ids[from_orig]
            to_int = mapa_ids[to_orig]
            
            if oneway_val == 1:
                edges.append((from_int, to_int, False))
            elif oneway_val == -1:
                edges.append((to_int, from_int, False))
            else:
                edges.append((from_int, to_int, True))
            
    return vertices, edges


def save_snapshot(path: Path, vertices: Dict[VertexId, Point], edges: List[Edge]) -> None:
    """
    Serializa o estado atual do grafo para o formato que o motor Java espera.
    Preenche lacunas de IDs com vértices "fantasmas" para manter índices estáveis.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    max_id = max(vertices.keys()) if vertices else -1
    total_to_write = max_id + 1
    
    with path.open("w", encoding="utf-8") as f:
        # Escreve cabeçalho com tamanho esperado pelo leitor Java.
        # Preenche índices ausentes com entradas neutras para manter compatibilidade.
        f.write(f"{total_to_write}\t2\t0\t1\n")
        for i in range(total_to_write):
            if i in vertices:
                x, y = vertices[i]
                f.write(f"{i}\t{str(x).replace('.', ',')}\t{str(y).replace('.', ',')}\t0\n")
            else:
                # Entrada neutra para índices ausentes, preservando contiguidades
                f.write(f"{i}\t0,0\t0,0\t0\n")

        # Escreve a lista de arestas e a flag de direção compatível com o parser Java
        f.write(f"{len(edges)}\t1\n")
        for i, edge in enumerate(edges):
            u, v = edge[0], edge[1]
            is_bidirectional = True
            if len(edge) >= 3:
                is_bidirectional = edge[2]
            direcional_flag = 0 if is_bidirectional else 1
            f.write(f"{i}\t{u}\t{v}\t{direcional_flag}\n")
        f.write("0")


def find_nearest_vertex(vertices: Dict[VertexId, Point], x: float, y: float) -> Tuple[VertexId | None, float]:
    """
    Retorna o vértice mais próximo da posição (x, y) e a distância ao quadrado.
    Calcula distância ao quadrado por eficiência (evita sqrt).
    """
    nearest = None
    nearest_dist_sq = float("inf") # Inicializa com infinito

    for id_no, (vx, vy) in vertices.items():
        # Calcula distância ao quadrado (Pitágoras sem raiz) por eficiência
        dist_sq = (vx - x) ** 2 + (vy - y) ** 2
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest = id_no

    return nearest, nearest_dist_sq


def create_vertex(vertices: Dict[VertexId, Point], x: float, y: float) -> VertexId:
    """
    Cria um novo vértice com ID incremental e retorna seu identificador.
    """
    # Gera novo ID incremental baseado no maior ID presente
    novo_id = max(vertices.keys()) + 1 if vertices else 0
    vertices[novo_id] = (x, y)
    return novo_id
