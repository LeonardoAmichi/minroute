import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsScene, QGraphicsObject
from PyQt6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, QRectF


class MapGraphicsView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, app_window):
        super().__init__(scene)
        self.app_window = app_window
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._last_pan_pos = None

    def wheelEvent(self, event):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.app_window.ao_clicar_mapa(scene_pos.x(), scene_pos.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.RightButton and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._last_pan_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            # Chama novo método no app.py para tratar o duplo clique (deletar)
            if hasattr(self.app_window, 'ao_duplo_clique_mapa'):
                self.app_window.ao_duplo_clique_mapa(scene_pos.x(), scene_pos.y())
        super().mouseDoubleClickEvent(event)


class PulsingDot(QGraphicsObject):
    """Ponto animado com efeito de pulso para origem/destino."""

    def __init__(self, x, y, color, parent=None):
        super().__init__(parent)
        self.setPos(x, y)
        self._color = QColor(color)
        self._radius = 8
        self._pulse_radius = 14.0
        self._pulse_opacity = 0.6
        self._expanding = True
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIgnoresTransformations)

        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)

    def _animate(self):
        if self._expanding:
            self._pulse_radius += 0.4
            self._pulse_opacity -= 0.02
            if self._pulse_radius >= 20:
                self._expanding = False
        else:
            self._pulse_radius -= 0.4
            self._pulse_opacity += 0.02
            if self._pulse_radius <= 14:
                self._expanding = True
        self._pulse_opacity = max(0.1, min(0.6, self._pulse_opacity))
        self.update()

    def boundingRect(self):
        return QRectF(-22, -22, 44, 44)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Anel de pulso
        pulse_color = QColor(self._color)
        pulse_color.setAlphaF(self._pulse_opacity)
        painter.setPen(QPen(pulse_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r = self._pulse_radius
        painter.drawEllipse(QRectF(-r, -r, r * 2, r * 2))
        # Ponto central
        painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
        painter.setBrush(QBrush(self._color))
        r2 = self._radius
        painter.drawEllipse(QRectF(-r2, -r2, r2 * 2, r2 * 2))

    def stop_pulse(self):
        self._timer.stop()


def draw_map(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list):
    pen_rua = QPen(QColor("#4c566a"))
    pen_rua.setWidthF(1.2)
    pen_rua.setCosmetic(True)

    path_ruas = QPainterPath()
    setas_oneway = []  # Lista de (cx, cy, angle) para desenhar setas depois

    for edge in edges:
        u = edge[0]
        v = edge[1]
        is_bidirectional = True
        if len(edge) >= 3:
            is_bidirectional = edge[2]

        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            
            path_ruas.moveTo(x1, y1)
            path_ruas.lineTo(x2, y2)
            
            # Apenas vias de mão única recebem setas
            if not is_bidirectional:
                dx = x2 - x1
                dy = y2 - y1
                dist = math.hypot(dx, dy)
                if dist > 0:
                    cx = x1 + dx / 2
                    cy = y1 + dy / 2
                    angle = math.atan2(dy, dx)
                    setas_oneway.append((cx, cy, angle, dist))

    scene.addPath(path_ruas, pen_rua)
    
    # Desenhar setas adaptativas de mão única
    # Tamanho uniforme baseado na mediana das ruas → adapta ao zoom naturalmente
    if setas_oneway:
        dists = sorted([s[3] for s in setas_oneway])
        mediana = dists[len(dists) // 2]
        sz = mediana * 0.2  # 20% da rua mediana — uniforme para todas

        path_setas = QPainterPath()
        for cx, cy, angle, _ in setas_oneway:
            path_setas.moveTo(cx + sz * math.cos(angle), cy + sz * math.sin(angle))
            path_setas.lineTo(cx + sz * math.cos(angle + 2.5), cy + sz * math.sin(angle + 2.5))
            path_setas.lineTo(cx + sz * math.cos(angle - 2.5), cy + sz * math.sin(angle - 2.5))
            path_setas.closeSubpath()
        
        item_setas = scene.addPath(path_setas, QPen(Qt.PenStyle.NoPen))
        item_setas.setBrush(QBrush(QColor(120, 130, 150, 160)))


def draw_labels(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list):
    labels = []

    # Pré-calcular conexões e distâncias para o tooltip
    adj = {vid: [] for vid in vertices}
    for edge in edges:
        u = edge[0]
        v = edge[1]
        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            dist = math.hypot(x1 - x2, y1 - y2)
            adj[u].append((v, dist))
            # O tooltip vai mostrar conexões para ambos os lados simplificadamente
            adj[v].append((u, dist)) 

    brush_v_dot = QBrush(QColor("#5e81ac"))

    for id_no, (x, y) in vertices.items():
        # Bolinha azul
        raio = 3.5  # Um pouco maior para facilitar o hover do mouse
        dot = QGraphicsEllipseItem(-raio, -raio, raio * 2, raio * 2)
        dot.setBrush(brush_v_dot)
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setPos(x, y)
        dot.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)

        # Tooltip rico
        tooltip = f"<div style='background-color: #2b2b2b; color: #DCE4EE; padding: 5px; border-radius: 4px;'>"
        tooltip += f"<b>Vértice ID: {id_no}</b>"
        if adj[id_no]:
            tooltip += "<br>Conexões:"
            # Limitar para não ficar gigante caso seja um hub muito conectado
            for v, dist in adj[id_no][:8]:
                tooltip += f"<br>&nbsp;&nbsp;➔ Vértice {v} (Peso: {dist:.1f} u.m.)"
            if len(adj[id_no]) > 8:
                tooltip += f"<br>&nbsp;&nbsp;... (+{len(adj[id_no]) - 8} arestas)"
        tooltip += "</div>"

        dot.setToolTip(tooltip)

        dot.hide()
        scene.addItem(dot)
        labels.append(dot)

    return labels


def draw_point(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], id_no: int, color: str, track_items: list):
    """Desenha um ponto pulsante sobre o vértice selecionado."""
    x, y = vertices[id_no]
    dot = PulsingDot(x, y, color)
    scene.addItem(dot)
    track_items.append(dot)
    return dot


def draw_route(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], caminho: list[int], track_items: list):
    """Desenha a rota com gradiente de cor: vermelho (origem) → verde (destino), com setas de direção."""
    if len(caminho) < 2:
        return

    total_segments = len(caminho) - 1
    # Intervalo entre setas: a cada N segmentos (mínimo 1)
    intervalo_setas = max(1, total_segments // 12)

    for i in range(total_segments):
        if total_segments == 1:
            t = 0.5
        else:
            t = i / (total_segments - 1)

        # Interpolar de vermelho (#ff4c4c) para verde (#50fa7b)
        r = int(255 * (1 - t) + 80 * t)
        g = int(76 * (1 - t) + 250 * t)
        b = int(76 * (1 - t) + 123 * t)

        color = QColor(r, g, b)
        pen = QPen(color)
        pen.setWidth(4)
        pen.setCosmetic(True)

        x1, y1 = vertices[caminho[i]]
        x2, y2 = vertices[caminho[i + 1]]

        line = scene.addLine(x1, y1, x2, y2, pen)
        track_items.append(line)

    # Pré-calcular tamanho uniforme das setas baseado na mediana dos segmentos
    seg_dists = []
    for i in range(total_segments):
        x1, y1 = vertices[caminho[i]]
        x2, y2 = vertices[caminho[i + 1]]
        seg_dists.append(math.hypot(x2 - x1, y2 - y1))
    seg_dists.sort()
    mediana = seg_dists[len(seg_dists) // 2] if seg_dists else 1
    sz = mediana * 0.3  # 30% da rua mediana da rota

    for i in range(total_segments):
        if i % intervalo_setas == 0:
            if total_segments == 1:
                t = 0.5
            else:
                t = i / (total_segments - 1)
            r = int(255 * (1 - t) + 80 * t)
            g = int(76 * (1 - t) + 250 * t)
            b = int(76 * (1 - t) + 123 * t)
            color = QColor(r, g, b)

            x1, y1 = vertices[caminho[i]]
            x2, y2 = vertices[caminho[i + 1]]
            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy)
            if dist > 0:
                cx = x1 + dx * 0.55
                cy = y1 + dy * 0.55
                angle = math.atan2(dy, dx)

                arrow_path = QPainterPath()
                arrow_path.moveTo(cx + sz * math.cos(angle), cy + sz * math.sin(angle))
                arrow_path.lineTo(cx + sz * math.cos(angle + 2.5), cy + sz * math.sin(angle + 2.5))
                arrow_path.lineTo(cx + sz * math.cos(angle - 2.5), cy + sz * math.sin(angle - 2.5))
                arrow_path.closeSubpath()

                arrow_item = scene.addPath(arrow_path, QPen(Qt.PenStyle.NoPen))
                arrow_item.setBrush(QBrush(color))
                track_items.append(arrow_item)
