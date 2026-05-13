import sys
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGraphicsView,
                             QGraphicsScene, QFrame, QGraphicsEllipseItem)
from PyQt6.QtGui import QPen, QColor, QBrush, QPainter, QFont, QPainterPath
from PyQt6.QtCore import Qt

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.map_model import create_vertex, find_nearest_vertex, load_poly, save_snapshot
from utils.java_bridge import run_dijkstra
from ui.renderer import (MapGraphicsView, draw_map, draw_point,
                         draw_permanent_point, draw_route)


class MinRouteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MinRoute - Sistema de Navegação (Motor Qt)")
        self.resize(1100, 700)

        self.caminho_mapa_original = "data/Campus2UFG&Regiao.poly"
        self.caminho_mapa_editado = "data/mapa_editado.poly"

        self.vertices = {}
        self.todas_arestas = []

        self.origem = None
        self.destino = None
        self.itens_rota = []
        self.modo_edicao_ativo = False
        self.no_edicao_selecionado = None

        self.configurar_layout()
        self.carregar_e_desenhar_mapa()

    def configurar_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #2b2b2b; color: #DCE4EE;")
        layout_sidebar = QVBoxLayout(sidebar)

        lbl_logo = QLabel("MinRoute")
        lbl_logo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
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

        layout_sidebar.addSpacing(20)

        self.btn_copiar = QPushButton("Copiar Imagem")
        self.btn_copiar.setStyleSheet("background-color: #4c566a; color: white; padding: 10px; border-radius: 5px;")
        self.btn_copiar.clicked.connect(self.copiar_imagem)
        layout_sidebar.addWidget(self.btn_copiar)

        self.btn_edicao = QPushButton("Ativar Modo Edição")
        self.btn_edicao.setCheckable(True)
        self.btn_edicao.setStyleSheet("background-color: #bf616a; color: white; padding: 10px; border-radius: 5px;")
        self.btn_edicao.toggled.connect(self.alternar_modo_edicao)
        layout_sidebar.addWidget(self.btn_edicao)

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

        self.lbl_status = QLabel("Clique no mapa para definir origem e destino.")
        self.lbl_status.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Normal))
        self.lbl_status.setStyleSheet(
            "color: #c8c8c8; padding: 8px 10px; border-radius: 8px; background-color: rgba(255,255,255,0.04);"
        )
        self.lbl_status.setWordWrap(True)
        layout_sidebar.addWidget(self.lbl_status)

        layout_sidebar.addStretch()
        layout_principal.addWidget(sidebar)

        self.scene = QGraphicsScene()
        self.view = MapGraphicsView(self.scene, self)
        layout_principal.addWidget(self.view)

    def carregar_e_desenhar_mapa(self):
        mapa_path = Path(self.caminho_mapa_original)
        if not mapa_path.exists():
            return

        try:
            self.vertices, self.todas_arestas = load_poly(mapa_path)
            draw_map(self.scene, self.vertices, self.todas_arestas)

            rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(rect.adjusted(-500, -500, 500, 500))
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Erro: {e}")

    def alternar_modo_edicao(self, ativo):
        self.modo_edicao_ativo = ativo
        if ativo:
            self.btn_edicao.setText("Desativar Modo Edição")
            self.btn_edicao.setStyleSheet("background-color: #a3be8c; color: white; padding: 10px; border-radius: 5px;")
            self.limpar_rota()
            self.update_status("Modo edição ativado. Clique para criar ou conectar nós.")
        else:
            self.btn_edicao.setText("Ativar Modo Edição")
            self.btn_edicao.setStyleSheet("background-color: #bf616a; color: white; padding: 10px; border-radius: 5px;")
            self.no_edicao_selecionado = None
            self.update_status("Clique no mapa para definir origem e destino.")

    def update_status(self, mensagem: str, sucesso: bool = True):
        cor = "#a0a0a0" if sucesso else "#f2b944"
        self.lbl_status.setText(mensagem)
        self.lbl_status.setStyleSheet(
            f"color: {cor}; padding: 8px 10px; border-radius: 8px; background-color: rgba(255,255,255,0.05);"
        )

    def ao_clicar_mapa(self, x_clique, y_clique):
        no_mais_proximo, menor_dist_sq = find_nearest_vertex(self.vertices, x_clique, y_clique)
        zoom = self.view.transform().m11()
        clicou_no_vazio = menor_dist_sq > (18 / zoom) ** 2

        if self.modo_edicao_ativo:
            if clicou_no_vazio:
                novo_id = create_vertex(self.vertices, x_clique, y_clique)
                self.desenhar_ponto_permanente(x_clique, y_clique, "#b48ead")
                print(f"Vértice {novo_id} criado.")
            else:
                if self.no_edicao_selecionado is None:
                    self.no_edicao_selecionado = no_mais_proximo
                    self.desenhar_ponto(no_mais_proximo, "#b48ead")
                elif self.no_edicao_selecionado != no_mais_proximo:
                    self.todas_arestas.append((self.no_edicao_selecionado, no_mais_proximo))
                    x1, y1 = self.vertices[self.no_edicao_selecionado]
                    x2, y2 = self.vertices[no_mais_proximo]
                    pen = QPen(QColor("#d08770"))
                    pen.setWidthF(2.0)
                    pen.setCosmetic(True)
                    self.scene.addLine(x1, y1, x2, y2, pen)
                    self.no_edicao_selecionado = None
                    self.limpar_rota()
            return

        if not clicou_no_vazio:
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

    def desenhar_ponto_permanente(self, x, y, cor):
        draw_permanent_point(self.scene, x, y, cor)

    def desenhar_ponto(self, id_no, cor):
        draw_point(self.scene, self.vertices, id_no, cor, self.itens_rota)

    def tracar_caminho(self):
        if self.origem is None or self.destino is None:
            return

        try:
            save_snapshot(Path(self.caminho_mapa_editado), self.vertices, self.todas_arestas)

            projeto_root = Path(__file__).resolve().parents[2]
            java_cp = projeto_root / "build" / "classes"
            dados = run_dijkstra(java_cp, Path(self.caminho_mapa_editado), self.origem, self.destino)

            caminho = dados.get("caminho", [])
            if caminho:
                draw_route(self.scene, self.vertices, caminho, self.itens_rota)
                self.lbl_tempo.setText(f"Tempo: {dados['tempo_ms']} ms")
                self.lbl_nos.setText(f"Nós explorados: {dados['nos_explorados']}")
                self.lbl_custo.setText(f"Distância: {dados['distancia_total']:.2f} u.m.")
                self.update_status("Rota encontrada com sucesso.")
            else:
                self.update_status("Nenhum caminho possível entre os pontos selecionados.", sucesso=False)
        except Exception as e:
            self.update_status("Erro ao calcular rota. Veja o console para detalhes.", sucesso=False)
            print(f"Erro na integração: {e}")

    def limpar_rota(self):
        for item in self.itens_rota:
            self.scene.removeItem(item)
        self.itens_rota.clear()
        self.origem = self.destino = None
        self.lbl_tempo.setText("Tempo: -- ms")
        self.lbl_nos.setText("Nós explorados: --")
        self.lbl_custo.setText("Distância: -- u.m.")
        self.update_status("Clique no mapa para definir origem e destino.")

    def copiar_imagem(self):
        QApplication.clipboard().setPixmap(self.view.grab())
        print("Copiado!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MinRouteApp()
    win.show()
    sys.exit(app.exec())