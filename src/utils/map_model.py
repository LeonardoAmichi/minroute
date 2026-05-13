from pathlib import Path
from typing import Dict, List, Tuple

VertexId = int
Point = Tuple[float, float]
Edge = Tuple[int, int]


def load_poly(path: Path) -> Tuple[Dict[VertexId, Point], List[Edge]]:
    vertices: Dict[VertexId, Point] = {}
    edges: List[Edge] = []

    with path.open("r", encoding="utf-8") as f:
        total_vertices = int(f.readline().split()[0])
        for _ in range(total_vertices):
            partes = f.readline().split()
            id_no = int(partes[0])
            x = float(partes[1].replace(",", "."))
            y = float(partes[2].replace(",", "."))
            vertices[id_no] = (x, y)

        total_arestas = int(f.readline().split()[0])
        for _ in range(total_arestas):
            partes = f.readline().split()
            u = int(partes[1])
            v = int(partes[2])
            edges.append((u, v))

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
