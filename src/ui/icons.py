from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QIcon, QPixmap, QPainterPath
from PyQt6.QtCore import Qt


class IconFactory:
    """Fábrica de ícones vetoriais minimalistas desenhados com QPainter."""

    @staticmethod
    def _make(size, draw_fn, color):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_fn(p, QColor(color), size)
        p.end()
        return QIcon(pix)

    @staticmethod
    def importar():
        def draw(p, c, s):
            pen = QPen(c, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            mid = s // 2
            p.drawLine(mid, 2, mid, s // 2 + 2)
            p.drawLine(mid - 3, s // 2 - 1, mid, s // 2 + 2)
            p.drawLine(mid + 3, s // 2 - 1, mid, s // 2 + 2)
            p.drawLine(2, s - 3, s - 2, s - 3)
            p.drawLine(2, s // 2 + 1, 2, s - 3)
            p.drawLine(s - 2, s // 2 + 1, s - 2, s - 3)
        return IconFactory._make(18, draw, "#FFFFFF")

    @staticmethod
    def navegacao():
        def draw(p, c, s):
            path = QPainterPath()
            path.moveTo(3, 2)
            path.lineTo(s - 2, s // 2)
            path.lineTo(3, s - 2)
            path.lineTo(5, s // 2)
            path.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawPath(path)
        return IconFactory._make(18, draw, "#5e9fd4")

    @staticmethod
    def limpar():
        def draw(p, c, s):
            pen = QPen(c, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(4, 4, s - 4, s - 4)
            p.drawLine(s - 4, 4, 4, s - 4)
        return IconFactory._make(18, draw, "#DCE4EE")

    @staticmethod
    def edicao():
        def draw(p, c, s):
            pen = QPen(c, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(3, s - 3, s - 3, 3)
            p.drawLine(s - 3, 3, s - 5, 3)
            p.drawLine(s - 3, 3, s - 3, 5)
        return IconFactory._make(18, draw, "#FFFFFF")

    @staticmethod
    def rotulos():
        def draw(p, c, s):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawEllipse(s // 2 - 4, s // 2 - 4, 8, 8)
        return IconFactory._make(18, draw, "#88c0d0")

    @staticmethod
    def copiar():
        def draw(p, c, s):
            pen = QPen(c, 1.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(1, 1, 8, 8)
            p.drawRect(6, 6, 8, 8)
        return IconFactory._make(18, draw, "#DCE4EE")

    @staticmethod
    def remover():
        def draw(p, c, s):
            pen = QPen(c, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawEllipse(2, 2, s - 4, s - 4)
            p.drawLine(5, s // 2, s - 5, s // 2)
        return IconFactory._make(18, draw, "#bf616a")
