import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsObject
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
            shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.app_window.ao_clicar_mapa(scene_pos.x(), scene_pos.y(), shift_pressed)
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


def draw_map(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list[tuple[int, int]]):
    pen_rua = QPen(QColor("#4c566a"))
    pen_rua.setWidthF(1.2)
    pen_rua.setCosmetic(True)

    path_mapa = QPainterPath()
    for u, v in edges:
        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            path_mapa.moveTo(x1, y1)
            path_mapa.lineTo(x2, y2)

    return scene.addPath(path_mapa, pen_rua)


def draw_labels(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list[tuple[int, int]]):
    labels = []

    # Pré-calcular conexões e distâncias para o tooltip
    adj = {vid: [] for vid in vertices}
    for u, v in edges:
        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            dist = math.hypot(x1 - x2, y1 - y2)
            adj[u].append((v, dist))
            adj[v].append((u, dist)) # Assumindo grafo bidirecional visualmente

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
                tooltip += f"<br>&nbsp;&nbsp;➔ {v}: {dist:.1f} u.m."
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
    """Desenha a rota com gradiente de cor: vermelho (origem) → verde (destino)."""
    if len(caminho) < 2:
        return

    total_segments = len(caminho) - 1

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
