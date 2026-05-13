from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsScene
from PyQt6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt


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


def draw_map(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list[tuple[int, int]]):
    pen_rua = QPen(QColor("#4c566a"))
    pen_rua.setWidthF(1.2)
    pen_rua.setCosmetic(True)

    path_mapa = QPainterPath()
    for u, v in edges:
        x1, y1 = vertices[u]
        x2, y2 = vertices[v]
        path_mapa.moveTo(x1, y1)
        path_mapa.lineTo(x2, y2)

    return scene.addPath(path_mapa, pen_rua)


def draw_permanent_point(scene: QGraphicsScene, x: float, y: float, color: str):
    raio = 5
    elipse = QGraphicsEllipseItem(-raio, -raio, raio * 2, raio * 2)
    elipse.setBrush(QBrush(QColor(color)))
    elipse.setPos(x, y)
    elipse.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)
    scene.addItem(elipse)
    return elipse


def draw_point(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], id_no: int, color: str, track_items: list):
    x, y = vertices[id_no]
    raio = 8
    elipse = QGraphicsEllipseItem(-raio, -raio, raio * 2, raio * 2)
    elipse.setPen(QPen(Qt.GlobalColor.white))
    elipse.setBrush(QBrush(QColor(color)))
    elipse.setPos(x, y)
    elipse.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)
    scene.addItem(elipse)
    track_items.append(elipse)
    return elipse


def draw_route(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], caminho: list[int], track_items: list):
    pen = QPen(QColor("#ebcb8b"))
    pen.setWidth(4)
    pen.setCosmetic(True)

    path = QPainterPath()
    x0, y0 = vertices[caminho[0]]
    path.moveTo(x0, y0)
    for id_no in caminho[1:]:
        x, y = vertices[id_no]
        path.lineTo(x, y)

    track_items.append(scene.addPath(path, pen))
