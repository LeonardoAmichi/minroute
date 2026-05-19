from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
import math

VertexId = int
Point = Tuple[float, float]
Edge = Tuple[int, int]


def load_poly(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []

    with path.open("r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]
        if not linhas:
            return {}, []
            
        idx = 0
        total_vertices = int(linhas[idx].split()[0])
        idx += 1
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
        for _ in range(total_arestas):
            if idx >= len(linhas): break
            partes = linhas[idx].split()
            if len(partes) >= 3:
                u = int(partes[1])
                v = int(partes[2])
                edges.append((u, v))
            idx += 1

    return vertices, edges


def load_osm(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []
    
    RAIO_TERRA = 6378137.0
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    vertices_temp = {}
    
    for node in root.findall('node'):
        id_str = node.get('id')
        lat_str = node.get('lat')
        lon_str = node.get('lon')
        if id_str and lat_str and lon_str:
            id_no = int(id_str)
            lat = float(lat_str)
            lon = float(lon_str)
            
            x = RAIO_TERRA * math.radians(lon)
            y = RAIO_TERRA * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
            
            vertices_temp[id_no] = (x, y)
            
    mapa_ids = {}
    novo_id = 0
    for old_id, point in vertices_temp.items():
        mapa_ids[old_id] = novo_id
        vertices[novo_id] = point
        novo_id += 1
        
    for way in root.findall('way'):
        nds = way.findall('nd')
        via = []
        for nd in nds:
            ref_str = nd.get('ref')
            if ref_str:
                ref = int(ref_str)
                if ref in vertices_temp:
                    via.append(ref)
                    
        for i in range(len(via) - 1):
            from_orig = via[i]
            to_orig = via[i+1]
            
            from_int = mapa_ids[from_orig]
            to_int = mapa_ids[to_orig]
            
            edges.append((from_int, to_int))
            
    return vertices, edges


def save_snapshot(path: Path, vertices: Dict[VertexId, Point], edges: List[Edge]) -> None:
    max_id = max(vertices.keys()) if vertices else -1
    total_to_write = max_id + 1
    
    with path.open("w", encoding="utf-8") as f:
        # O Java usa o primeiro valor como tamanho do array e limite do loop de leitura.
        # Para evitar ArrayIndexOutOfBounds e erros de leitura, preenchemos os gaps.
        f.write(f"{total_to_write}\t2\t0\t1\n")
        for i in range(total_to_write):
            if i in vertices:
                x, y = vertices[i]
                f.write(f"{i}\t{str(x).replace('.', ',')}\t{str(y).replace('.', ',')}\t0\n")
            else:
                # Vértice "fantasma" para manter a integridade dos índices no Java
                f.write(f"{i}\t0,0\t0,0\t0\n")

        f.write(f"{len(edges)}\t1\n")
        for i, (u, v) in enumerate(edges):
            f.write(f"{i}\t{u}\t{v}\t0\n")
        f.write("0")


def find_nearest_vertex(vertices: Dict[VertexId, Point], x: float, y: float) -> Tuple[VertexId | None, float]:
    nearest = None
    nearest_dist_sq = float("inf")

    for id_no, (vx, vy) in vertices.items():
        dist_sq = (vx - x) ** 2 + (vy - y) ** 2
        if dist_sq < nearest_dist_sq:
            nearest_dist_sq = dist_sq
            nearest = id_no

    return nearest, nearest_dist_sq


def create_vertex(vertices: Dict[VertexId, Point], x: float, y: float) -> VertexId:
    novo_id = max(vertices.keys()) + 1 if vertices else 0
    vertices[novo_id] = (x, y)
    return novo_id
