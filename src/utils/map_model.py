from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
import math

# Criando apelidos (aliases) para facilitar a leitura do código
VertexId = int
Point = Tuple[float, float]
Edge = Tuple[int, int, bool]


def load_txt(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Lê um arquivo de mapa no formato texto simples (.txt).
    Ele pula comentários, entende o cabeçalho e constrói a lista de pontos e ruas.
    """
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []

    with path.open("r", encoding="utf-8") as f:
        # Lê todas as linhas, tirando espaços e ignorando comentários
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
                # Trocamos vírgula por ponto para o Python não se confundir
                x = float(partes[1].replace(",", "."))
                y = float(partes[2].replace(",", "."))
                vertices[id_no] = (x, y)
            idx += 1
            
        # Lendo as ruas (arestas) que conectam os pontos
        for _ in range(m):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 2:
                u = int(partes[0])
                v = int(partes[1])
                is_bidirectional = True
                # A terceira coluna, se existir, avisa se é mão única ou dupla
                if len(partes) >= 3:
                    is_bidirectional = (int(partes[2]) == 0)
                edges.append((u, v, is_bidirectional))
            idx += 1

    return vertices, edges


def load_poly(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Lê arquivos do tipo .poly, que têm uma estrutura parecida com o .txt,
    mas o cabeçalho é dividido em várias linhas.
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
        
        # Pega as coordenadas X e Y
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
        
        # Pega de onde a rua sai e pra onde ela vai
        for _ in range(total_arestas):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 3:
                u = int(partes[1])
                v = int(partes[2])
                is_bidirectional = True
                # Verifica a regra de mão da rua
                if len(partes) >= 4:
                    is_bidirectional = (int(partes[3]) == 0)
                edges.append((u, v, is_bidirectional))
            idx += 1

    return vertices, edges


def load_osm(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    """
    Desvenda os segredos de um arquivo XML do OpenStreetMap.
    Ele converte coordenadas da Terra para coordenadas de tela plana.
    """
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []
    
    # Nossa pequena Terra em metros
    RAIO_TERRA = 6378137.0
    
    # O Python consegue ler o XML de forma iterativa para não estourar a memória RAM
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
                
                # Aqui rola uma matemática mágica para "achatar" a terra (Mercator)
                x = RAIO_TERRA * math.radians(lon)
                y = RAIO_TERRA * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
                
                vertices_temp[id_no] = (x, y)
            elem.clear() # Limpa o nó XML da memória
            
        elif elem.tag == 'way':
            nds = elem.findall('nd')
            via = []
            for nd in nds:
                ref_str = nd.get('ref')
                if ref_str:
                    ref = int(ref_str)
                    if ref in vertices_temp:
                        via.append(ref)
                        
            # Descobre se a rua é contramão, mão dupla, etc
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
                
            elem.clear() # Limpa a via XML da memória

    # O OSM usa IDs monstruosos de tamanho. Vamos transformá-los em números de 0, 1, 2...
    mapa_ids = {}
    novo_id = 0
    for old_id, point in vertices_temp.items():
        mapa_ids[old_id] = novo_id
        vertices[novo_id] = point
        novo_id += 1
        
    # 2. Liga os pontinhos de dois em dois seguindo as regras de trânsito
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
    Tira uma "foto" (salva o estado) de como o mapa está no momento para que
    o Java possa ler a versão mais recente caso a gente tenha editado.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    max_id = max(vertices.keys()) if vertices else -1
    total_to_write = max_id + 1
    
    with path.open("w", encoding="utf-8") as f:
        # O Java usa o primeiro valor como tamanho do array e limite do loop de leitura.
        # Para evitar ArrayIndexOutOfBounds e erros de leitura, preenchemos os buracos (gaps).
        f.write(f"{total_to_write}\t2\t0\t1\n")
        for i in range(total_to_write):
            if i in vertices:
                x, y = vertices[i]
                f.write(f"{i}\t{str(x).replace('.', ',')}\t{str(y).replace('.', ',')}\t0\n")
            else:
                # Vértice "fantasma" para manter a integridade dos índices no Java
                f.write(f"{i}\t0,0\t0,0\t0\n")

        # Escreve as conexões atualizadas
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
    Quando o usuário clica na tela, essa função busca qual é o pontinho (vértice) mais perto do mouse.
    """
    nearest = None
    nearest_dist_sq = float("inf") # Começamos achando que o mais perto está no infinito

    for id_no, (vx, vy) in vertices.items():
        # Usa Pitágoras (sem tirar a raiz para ficar mais rápido) para ver quem tá mais perto
        dist_sq = (vx - x) ** 2 + (vy - y) ** 2
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest = id_no

    return nearest, nearest_dist_sq


def create_vertex(vertices: Dict[VertexId, Point], x: float, y: float) -> VertexId:
    """
    Cria um ponto novinho em folha na coordenada X e Y fornecida.
    """
    # Acha o último número usado para dar um ID inédito para ele
    novo_id = max(vertices.keys()) + 1 if vertices else 0
    vertices[novo_id] = (x, y)
    return novo_id
