import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsScene, QGraphicsObject
from PyQt6.QtGui import QBrush, QFont, QPainter, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal


class MapGraphicsView(QGraphicsView):
    """
    Visualização do mapa: trata interações de mouse (clique, arraste, zoom)
    e emite sinal quando a escala é alterada.
    """
    zoom_changed = pyqtSignal(float)

    def __init__(self, scene: QGraphicsScene, app_window):
        super().__init__(scene)
        self.app_window = app_window
        # Habilita antialiasing para suavizar traços
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Define o ponto de ancoragem do zoom sob o cursor do mouse
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        # Define cor de fundo escura para o mapa
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        # Desativa barras de rolagem horizontais e verticais
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._last_pan_pos = None

    def wheelEvent(self, event):
        """Aplica zoom relativo ao movimento da roda do mouse."""
        # Rodada positiva -> zoom in; negativa -> zoom out (fator ~15%)
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)
        self.zoom_changed.emit(self.transform().m11())

    def mousePressEvent(self, event):
        """Processa evento de pressionamento de botão do mouse."""
        if event.button() == Qt.MouseButton.RightButton:
            # Botão direito: inicia arraste (pan) do mapa
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Botão esquerdo: notifica a janela principal sobre a posição do clique
            scene_pos = self.mapToScene(event.pos())
            self.app_window.ao_clicar_mapa(scene_pos.x(), scene_pos.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Processa movimento do mouse e realiza pan quando o botão direito estiver ativo."""
        if event.buttons() & Qt.MouseButton.RightButton and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            # Desliza a visualização atual para simular arraste do mapa
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Restaura estado ao soltar o botão do mouse (ex.: cursor)."""
        if event.button() == Qt.MouseButton.RightButton:
            self._last_pan_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Ao duplo clique, encaminha evento ao app principal (ex.: remoção de vértice)."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            # Invoca handler de duplo clique no app principal, se disponível
            if hasattr(self.app_window, 'ao_duplo_clique_mapa'):
                self.app_window.ao_duplo_clique_mapa(scene_pos.x(), scene_pos.y())
        super().mouseDoubleClickEvent(event)


class PulsingDot(QGraphicsObject):
    """Ponto animado com efeito de pulso (parece um radar) para destacar a origem e o destino."""

    def __init__(self, x, y, color, parent=None):
        super().__init__(parent)
        self.setPos(x, y)
        self._color = QColor(color)
        self._radius = 8
        self._pulse_radius = 14.0
        self._pulse_opacity = 0.6
        self._expanding = True
        # Ignora as transformações da tela para que a bolinha não fique gigante quando damos zoom no mapa
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIgnoresTransformations)

        # Inicia um cronômetro que "pisca" a bolinha a cada 40 milissegundos
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)

    def _animate(self):
        """Atualiza estado do pulso e solicita redesenho do item animado."""
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
        self.update() # Solicita redesenho com novos parâmetros de pulso

    def boundingRect(self):
        """Retorna a área ocupada pelo item para o sistema de renderização."""
        return QRectF(-22, -22, 44, 44)

    def paint(self, painter, option, widget=None):
        """Renderiza o ponto e seu anel de pulso com antialiasing."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Anel de pulso (efeito de destaque)
        pulse_color = QColor(self._color)
        pulse_color.setAlphaF(self._pulse_opacity)
        painter.setPen(QPen(pulse_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r = self._pulse_radius
        painter.drawEllipse(QRectF(-r, -r, r * 2, r * 2))
        
        # Ponto central (marcador)
        painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
        painter.setBrush(QBrush(self._color))
        r2 = self._radius
        painter.drawEllipse(QRectF(-r2, -r2, r2 * 2, r2 * 2))

    def stop_pulse(self):
        """Para o temporizador para liberar recursos quando o item for removido."""
        self._timer.stop()


def draw_map(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list):
    """Desenha o grafo (arestas) na cena e retorna itens representando setas de vias one-way.
    Os itens retornados podem ser usados para alternar visibilidade posteriormente.
    """
    pen_rua = QPen(QColor("#4c566a"))
    pen_rua.setWidthF(1.2)
    pen_rua.setCosmetic(True) # Mantém espessura fixa em pixels independentemente do zoom

    path_ruas = QPainterPath()
    setas_oneway = []  # Lista de (cx, cy, angle, dist) para desenhar setas em vias direcionadas

    for edge in edges:
        u = edge[0]
        v = edge[1]
        is_bidirectional = True
        if len(edge) >= 3:
            is_bidirectional = edge[2]

        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            
            # Adiciona segmento da aresta ao caminho composto
            path_ruas.moveTo(x1, y1)
            path_ruas.lineTo(x2, y2)
            
            # Apenas vias direcionadas recebem setas indicativas de sentido
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
    
    # Setas cosméticas independentes do zoom: tamanho fixo em pixels para consistência visual
    itens_setas = []
    if setas_oneway:
        from PyQt6.QtWidgets import QGraphicsPathItem
        
        sz = 8.0  # Tamanho fixo em pixels na tela
        base_arrow = QPainterPath()
        base_arrow.moveTo(sz, 0)
        base_arrow.lineTo(sz * math.cos(2.5), sz * math.sin(2.5))
        base_arrow.lineTo(sz * math.cos(-2.5), sz * math.sin(-2.5))
        base_arrow.closeSubpath()
        
        brush = QBrush(QColor(120, 130, 150, 160))
        pen = QPen(Qt.PenStyle.NoPen)

        for cx, cy, angle, dist in setas_oneway:
            item = QGraphicsPathItem(base_arrow)
            item.setBrush(brush)
            item.setPen(pen)
            
            # Posiciona e rotaciona o item para coincidir com a aresta
            item.setPos(cx, cy)
            item.setRotation(math.degrees(angle))
            
            # Ignora transformações de zoom para manter tamanho constante em pixels
            item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations)
            
            # Armazena a distância da aresta para uso em LOD (Level of Detail)
            item.setData(0, dist)
            
            scene.addItem(item)
            itens_setas.append(item)

    return itens_setas


def draw_labels(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], edges: list):
    """Cria pontos interativos sobre vértices que exibem tooltip com informações.
    """
    labels = []

    # Pré-calcula adjacências e distâncias para montar os tooltips
    adj = {vid: [] for vid in vertices}
    for edge in edges:
        u = edge[0]
        v = edge[1]
        if u in vertices and v in vertices:
            x1, y1 = vertices[u]
            x2, y2 = vertices[v]
            dist = math.hypot(x1 - x2, y1 - y2)
            adj[u].append((v, dist))
            # Registra conexões em ambos sentidos para apresentação simplificada
            adj[v].append((u, dist)) 

    brush_v_dot = QBrush(QColor("#5e81ac"))

    for id_no, (x, y) in vertices.items():
        # Marcador pequeno para o vértice
        raio = 3.5  # Raio em pixels, levemente ampliado para facilitar interação
        dot = QGraphicsEllipseItem(-raio, -raio, raio * 2, raio * 2)
        dot.setBrush(brush_v_dot)
        dot.setPen(QPen(Qt.PenStyle.NoPen))
        dot.setPos(x, y)
        dot.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)

        # Constrói o HTML do tooltip exibindo informações do vértice
        tooltip = f"<div style='background-color: #2b2b2b; color: #DCE4EE; padding: 5px; border-radius: 4px;'>"
        tooltip += f"<b>Vértice ID: {id_no}</b>"
        if adj[id_no]:
            tooltip += "<br>Conexões:"
            # Limitar para não ficar gigante caso seja um cruzamento muito movimentado
            for v, dist in adj[id_no][:8]:
                tooltip += f"<br>&nbsp;&nbsp;➔ Vértice {v} (Peso: {dist:.1f} u.m.)"
            if len(adj[id_no]) > 8:
                tooltip += f"<br>&nbsp;&nbsp;... (+{len(adj[id_no]) - 8} arestas)"
        tooltip += "</div>"

        dot.setToolTip(tooltip)

        dot.hide() # Mantém oculto até que a exibição de rótulos seja ativada
        scene.addItem(dot)
        labels.append(dot)

    return labels


def draw_point(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], id_no: int, color: str, track_items: list):
    """Desenha um marcador animado (PulsingDot) sobre o vértice especificado."""
    x, y = vertices[id_no]
    dot = PulsingDot(x, y, color)
    scene.addItem(dot)
    track_items.append(dot)
    return dot


def draw_route(scene: QGraphicsScene, vertices: dict[int, tuple[float, float]], caminho: list[int], track_items: list):
    """Desenha a rota calculada pelo Dijkstra, com gradiente de cor e setas decorativas.
    Retorna itens de seta da rota para controle de visibilidade.
    """
    setas_rota = []

    if len(caminho) < 2:
        return setas_rota

    total_segments = len(caminho) - 1
    # Determina intervalo de setas decorativas ao longo da rota
    intervalo_setas = max(1, total_segments // 12)

    for i in range(total_segments):
        if total_segments == 1:
            t = 0.5
        else:
            t = i / (total_segments - 1)

        # Interpola a cor do gradiente entre vermelho (origem) e verde (destino)
        r = int(255 * (1 - t) + 80 * t)
        g = int(76 * (1 - t) + 250 * t)
        b = int(76 * (1 - t) + 123 * t)

        color = QColor(r, g, b)
        pen = QPen(color)
        pen.setWidth(4)
        pen.setCosmetic(True)

        x1, y1 = vertices[caminho[i]]
        x2, y2 = vertices[caminho[i + 1]]

        # Desenha o segmento da rota na cena
        line = scene.addLine(x1, y1, x2, y2, pen)
        track_items.append(line)

    # Adiciona setas decorativas ao longo da rota (tamanho fixo em pixels)
    from PyQt6.QtWidgets import QGraphicsPathItem

    sz = 11.0  # Tamanho fixo em pixels para a seta
    base_arrow = QPainterPath()
    base_arrow.moveTo(sz, 0)
    base_arrow.lineTo(-sz, sz * 0.6)
    base_arrow.lineTo(-sz, -sz * 0.6)
    base_arrow.closeSubpath()

    for i in range(total_segments):
        if i % intervalo_setas == 0:
            if total_segments == 1:
                t = 0.5
            else:
                t = i / (total_segments - 1)
            # Refaz o cálculo da cor para combinar com o degradê!
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

                arrow_item = scene.addPath(base_arrow, QPen(Qt.PenStyle.NoPen))
                arrow_item.setBrush(QBrush(color))
                
                # Posiciona no meio da aresta e gira para apontar no sentido do movimento
                arrow_item.setPos(cx, cy)
                arrow_item.setRotation(math.degrees(angle))
                
                # O Segredo: Ignora as transformações de zoom para manter a seta sempre do mesmo tamanho na tela!
                arrow_item.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations)
                
                track_items.append(arrow_item)
                setas_rota.append(arrow_item)

    return setas_rota
