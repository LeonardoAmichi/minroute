import sys
import os
import subprocess
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGraphicsView,
                             QGraphicsScene, QFrame, QGraphicsEllipseItem)
from PyQt6.QtGui import QPen, QColor, QBrush, QPainter, QFont, QPainterPath
from PyQt6.QtCore import Qt

class MapGraphicsView(QGraphicsView):
    def __init__(self, scene, app_window):
        super().__init__(scene)
        self.app_window = app_window
        # Antialiasing para deixar as linhas suaves
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Desativamos o drag padrão para implementar o manual no botão direito
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        
        # Remove as barras de rolagem para um visual limpo "estilo QGIS"
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._last_pan_pos = None

    def wheelEvent(self, event):
        # Controle de zoom fluido pela rodinha do mouse
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Inicia o pan com botão direito
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            # Seleção imediata com o esquerdo
            scene_pos = self.mapToScene(event.pos())
            self.app_window.ao_clicar_mapa(scene_pos.x(), scene_pos.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.RightButton and self._last_pan_pos is not None:
            # Calcula o deslocamento
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            
            # Move as barras de rolagem internas (mesmo que invisíveis) para deslocar o mapa
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._last_pan_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)


class MinRouteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MinRoute - Sistema de Navegação (Motor Qt)")
        self.resize(1100, 700)
        
        self.caminho_mapa = "data/Campus2UFG&Regiao.poly"
        
        self.vertices = {}
        self.origem = None
        self.destino = None
        self.itens_rota = [] # Guarda os desenhos (linhas/pontos) para apagar depois

        self.configurar_layout()
        self.carregar_e_desenhar_mapa()

    def configurar_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # ================= Sidebar (Painel de Controle) =================
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #2b2b2b; color: #DCE4EE;")
        layout_sidebar = QVBoxLayout(sidebar)
        
        fonte_titulo = QFont("Arial", 16, QFont.Weight.Bold)
        lbl_logo = QLabel("MinRoute")
        lbl_logo.setFont(fonte_titulo)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_sidebar.addWidget(lbl_logo)
        layout_sidebar.addSpacing(20)

        self.btn_tracar = QPushButton("Traçar Menor Caminho")
        self.btn_tracar.setStyleSheet("background-color: #1f538d; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        self.btn_tracar.clicked.connect(self.tracar_caminho)
        layout_sidebar.addWidget(self.btn_tracar)

        self.btn_limpar = QPushButton("Limpar Rota")
        self.btn_limpar.setStyleSheet("background-color: transparent; border: 1px solid #565b5e; color: #DCE4EE; padding: 10px; border-radius: 5px;")
        self.btn_limpar.clicked.connect(self.limpar_rota)
        layout_sidebar.addWidget(self.btn_limpar)

        layout_sidebar.addSpacing(40)
        lbl_stats = QLabel("Estatísticas da Execução:")
        layout_sidebar.addWidget(lbl_stats)

        fonte_stats = QFont("JetBrains Mono", 10)
        self.lbl_tempo = QLabel("Tempo: -- ms")
        self.lbl_tempo.setFont(fonte_stats)
        self.lbl_tempo.setStyleSheet("color: #a0a0a0;")
        layout_sidebar.addWidget(self.lbl_tempo)

        self.lbl_nos = QLabel("Nós explorados: --")
        self.lbl_nos.setFont(fonte_stats)
        self.lbl_nos.setStyleSheet("color: #a0a0a0;")
        layout_sidebar.addWidget(self.lbl_nos)

        self.lbl_custo = QLabel("Distância: -- u.m.")
        self.lbl_custo.setFont(fonte_stats)
        self.lbl_custo.setStyleSheet("color: #a0a0a0;")
        layout_sidebar.addWidget(self.lbl_custo)

        layout_sidebar.addStretch()
        layout_principal.addWidget(sidebar)

        # ================= Área do Mapa (Scene & View) =================
        self.scene = QGraphicsScene()
        self.view = MapGraphicsView(self.scene, self)
        layout_principal.addWidget(self.view)

    def carregar_e_desenhar_mapa(self):
        if not os.path.exists(self.caminho_mapa):
            print(f"Erro fatal: O arquivo {self.caminho_mapa} não foi encontrado.")
            return

        arestas_lidas = []
        try:
            with open(self.caminho_mapa, 'r') as f:
                linha = f.readline().split()
                total_vertices = int(linha[0])
                
                for _ in range(total_vertices):
                    partes = f.readline().split()
                    id_no = int(partes[0])
                    x = float(partes[1].replace(',', '.'))
                    y = float(partes[2].replace(',', '.'))
                    self.vertices[id_no] = (x, y)

                linha = f.readline().split()
                total_arestas = int(linha[0])
                
                for _ in range(total_arestas):
                    partes = f.readline().split()
                    arestas_lidas.append((int(partes[1]), int(partes[2])))

            # Desenha as arestas utilizando um único QPainterPath para performance extrema
            pen_rua = QPen(QColor("#4c566a"))
            pen_rua.setWidthF(1.2)
            pen_rua.setCosmetic(True) # Garante visibilidade constante independente do zoom
            
            path_mapa = QPainterPath()
            for origem, destino in arestas_lidas:
                x1, y1 = self.vertices[origem]
                x2, y2 = self.vertices[destino]
                path_mapa.moveTo(x1, y1)
                path_mapa.lineTo(x2, y2)
                
            self.scene.addPath(path_mapa, pen_rua)

            # Enquadramento inicial
            rect = self.scene.itemsBoundingRect()
            # Adiciona uma margem para o mapa não ficar colado nas bordas
            self.scene.setSceneRect(rect.adjusted(-500, -500, 500, 500))
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            print("Mapa renderizado através do Qt Engine!")
            
        except Exception as e:
            print(f"Erro ao processar o mapa: {e}")

    def ao_clicar_mapa(self, x_clique, y_clique):
        no_mais_proximo = None
        menor_dist_sq = float('inf')
        
        for id_no, (x, y) in self.vertices.items():
            dist_sq = (x - x_clique)**2 + (y - y_clique)**2
            if dist_sq < menor_dist_sq:
                menor_dist_sq = dist_sq
                no_mais_proximo = id_no
        
        # TOLERÂNCIA: Verifica se o clique foi perto o suficiente de um vértice
        # 15 pixels de raio, convertidos para o espaço do mapa
        zoom_atual = self.view.transform().m11()
        tolerancia_sq = (15 / zoom_atual)**2
        
        if menor_dist_sq > tolerancia_sq:
            return 
                
        if self.origem is None:
            self.limpar_rota()
            self.origem = no_mais_proximo
            self.desenhar_ponto(self.origem, "#ff4c4c")
        elif self.destino is None and no_mais_proximo != self.origem:
            self.destino = no_mais_proximo
            self.desenhar_ponto(self.destino, "#50fa7b")
        else:
            self.limpar_rota()
            self.origem = no_mais_proximo
            self.desenhar_ponto(self.origem, "#ff4c4c")

    def desenhar_ponto(self, id_no, cor_hex):
        x, y = self.vertices[id_no]
        raio = 8 # Ponto um pouco maior para facilitar visualização
        
        pen_ponto = QPen(Qt.GlobalColor.white)
        pen_ponto.setCosmetic(True)
        pen_ponto.setWidth(2)
        
        # A MÁGICA: Criamos a elipse na origem (0,0) relativa e a movemos para X,Y
        elipse = QGraphicsEllipseItem(-raio, -raio, raio * 2, raio * 2)
        elipse.setPen(pen_ponto)
        elipse.setBrush(QBrush(QColor(cor_hex)))
        elipse.setPos(x, y)
        
        # O ponto mantém o tamanho físico na tela independente do zoom (estilo QGIS)
        elipse.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)
        
        self.scene.addItem(elipse)
        self.itens_rota.append(elipse)

    def tracar_caminho(self):
        if self.origem is None or self.destino is None:
            return
            
        try:
            projeto_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            # O CLASSPATH CORRETO: onde os .class realmente vivem
            java_cp = os.path.join(projeto_root, "build", "classes")
            
            comando = [
                "java",
                "-cp",
                java_cp,
                "src.core.DijkstraCore",
                os.path.join(projeto_root, self.caminho_mapa),
                str(self.origem),
                str(self.destino)
            ]
            resultado = subprocess.run(comando, capture_output=True, text=True)
            
            if not resultado.stdout.strip():
                raise Exception(f"Java não retornou dados. Erro: {resultado.stderr}")
                
            dados = json.loads(resultado.stdout)
            
            caminho = dados.get('caminho', [])
            if not caminho or dados.get('distancia_total') == -1:
                print("Sem caminho possível.")
                return
                
            pen_rota = QPen(QColor("#ebcb8b"))
            pen_rota.setWidth(3)
            # A grossura da rota (3px) se mantém estável mesmo aplicando zoom máximo
            pen_rota.setCosmetic(True) 
            
            # Traça a rota toda em um único path para melhor performance e junções contínuas
            path_rota = QPainterPath()
            if caminho:
                x_start, y_start = self.vertices[caminho[0]]
                path_rota.moveTo(x_start, y_start)
                for id_no in caminho[1:]:
                    x, y = self.vertices[id_no]
                    path_rota.lineTo(x, y)
                    
            item_rota = self.scene.addPath(path_rota, pen_rota)
            self.itens_rota.append(item_rota)
                
            self.lbl_tempo.setText(f"Tempo: {dados['tempo_ms']} ms")
            self.lbl_nos.setText(f"Nós explorados: {dados['nos_explorados']}")
            self.lbl_custo.setText(f"Distância: {dados['distancia_total']:.2f} u.m.")
            
        except Exception as e:
            print(f"Falha de IPC com o Java: {e}")

    def limpar_rota(self):
        for item in self.itens_rota:
            self.scene.removeItem(item)
        self.itens_rota.clear()
        self.origem = None
        self.destino = None
        self.lbl_tempo.setText("Tempo: -- ms")
        self.lbl_nos.setText("Nós explorados: --")
        self.lbl_custo.setText("Distância: -- u.m.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MinRouteApp()
    window.show()
    sys.exit(app.exec())
