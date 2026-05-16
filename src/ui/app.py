import sys
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGraphicsView,
                             QGraphicsScene, QFrame, QGraphicsEllipseItem, QFileDialog)
from PyQt6.QtGui import QPen, QColor, QBrush, QPainter, QFont, QPainterPath, QIcon, QPixmap
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.map_model import create_vertex, find_nearest_vertex, load_poly, load_osm, save_snapshot
from utils.java_bridge import run_dijkstra
from ui.renderer import (MapGraphicsView, draw_map, draw_point, draw_route, draw_labels)
from ui.icons import IconFactory


class NotificationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.on_animation_finished)
        self._is_hiding = False
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)
        
        self.hide()

    def show_message(self, message, sucesso=True):
        self._is_hiding = False
        cor_fundo = "#2ecc71" if sucesso else "#e74c3c"
        self.label.setText(message)
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {cor_fundo};
                color: white;
                font-weight: bold;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 13px;
                border: 2px solid rgba(255,255,255,0.2);
            }}
        """)
        self.adjustSize()
        
        # Centralizar horizontalmente no topo
        parent_width = self.parent().width()
        x = (parent_width - self.width()) // 2
        
        self.start_pos = QPoint(x, -self.height())
        self.end_pos = QPoint(x, 20)
        
        self.move(self.start_pos)
        self.show()
        self.raise_()
        
        self.animation.stop()
        self.animation.setStartValue(self.start_pos)
        self.animation.setEndValue(self.end_pos)
        self.animation.start()
        
        self.timer.start(3500)

    def hide_notification(self):
        self._is_hiding = True
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(self.pos().x(), -self.height() - 10))
        self.animation.start()

    def on_animation_finished(self):
        if self._is_hiding:
            self.hide()
            self._is_hiding = False


class MinRouteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MinRoute - Sistema de Navegação (Motor Qt)")
        self.resize(1100, 700)

        self.caminho_mapa_original = None
        self.caminho_mapa_editado = "data/mapa_editado.poly"

        self.vertices = {}
        self.todas_arestas = []

        self.origem = None
        self.destino = None
        self.itens_rota = []
        self.labels = []
        self.modo_edicao_ativo = False
        self.no_edicao_selecionado = None

        self.vertices_edicao = set()  # Vértices criados ou selecionados na edição atual
        
        self.configurar_layout()
        self.notification = NotificationWidget(self.view)
        self.mostrar_estado_vazio()

    def configurar_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # Base da Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QFrame#Sidebar {
                background-color: #2b2b2b;
                border-right: 1px solid #1e1e1e;
            }
            QLabel {
                color: #DCE4EE;
                font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
                border: none;
            }
            QPushButton {
                font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
                font-size: 13px;
                padding: 10px 5px;
                border-radius: 6px;
                border: none;
                text-align: center;
            }
        """)
        layout_sidebar = QVBoxLayout(sidebar)
        layout_sidebar.setContentsMargins(20, 25, 20, 20)
        layout_sidebar.setSpacing(15)

        # Logo
        lbl_logo = QLabel("MinRoute")
        lbl_logo.setFont(QFont("Segoe UI", 18, QFont.Weight.ExtraBold))
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("margin-bottom: 10px; border: none;")
        layout_sidebar.addWidget(lbl_logo)

        # ── SEÇÃO: Dados do Mapa ──
        layout_sidebar.addWidget(self._criar_separador())
        lbl_file = QLabel("DADOS DO MAPA")
        lbl_file.setStyleSheet("color: #808080; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout_sidebar.addWidget(lbl_file)

        self.btn_importar = QPushButton("Importar Mapa")
        self.btn_importar.setIcon(IconFactory.importar())
        self.btn_importar.setStyleSheet("""
            QPushButton { background-color: #e67e22; color: white; font-weight: bold; }
            QPushButton:hover { background-color: #d35400; }
            QPushButton:pressed { background-color: #a04000; }
        """)
        self.btn_importar.clicked.connect(self.importar_mapa)
        layout_sidebar.addWidget(self.btn_importar)

        self.lbl_mapa_atual = QLabel("Nenhum mapa carregado")
        self.lbl_mapa_atual.setStyleSheet("color: #606060; font-size: 10px; font-style: italic; border: none; padding-left: 2px;")
        self.lbl_mapa_atual.setWordWrap(True)
        layout_sidebar.addWidget(self.lbl_mapa_atual)

        self.btn_remover = QPushButton("Remover Mapa")
        self.btn_remover.setIcon(IconFactory.remover())
        self.btn_remover.setStyleSheet("""
            QPushButton { background-color: transparent; border: 1px solid #565b5e; color: #bf616a; }
            QPushButton:hover { background-color: #3a2020; border-color: #bf616a; }
        """)
        self.btn_remover.clicked.connect(self.remover_mapa)
        self.btn_remover.hide()
        layout_sidebar.addWidget(self.btn_remover)

        # ── SEÇÃO: Navegação ──
        layout_sidebar.addWidget(self._criar_separador())
        lbl_nav = QLabel("NAVEGAÇÃO")
        lbl_nav.setStyleSheet("color: #808080; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout_sidebar.addWidget(lbl_nav)

        self.lbl_origem = QLabel("Origem: --")
        self.lbl_origem.setStyleSheet("color: #ff4c4c; font-size: 11px; border: none; padding-left: 2px;")
        layout_sidebar.addWidget(self.lbl_origem)

        self.lbl_destino = QLabel("Destino: --")
        self.lbl_destino.setStyleSheet("color: #50fa7b; font-size: 11px; border: none; padding-left: 2px;")
        layout_sidebar.addWidget(self.lbl_destino)

        self.btn_tracar = QPushButton("Traçar Menor Caminho")
        self.btn_tracar.setIcon(IconFactory.navegacao())
        self.btn_tracar.setStyleSheet("""
            QPushButton { background-color: #1f538d; color: white; font-weight: bold; }
            QPushButton:hover { background-color: #2a6db8; }
            QPushButton:pressed { background-color: #14365d; }
        """)
        self.btn_tracar.clicked.connect(self.tracar_caminho)
        layout_sidebar.addWidget(self.btn_tracar)

        self.btn_limpar = QPushButton("Limpar Rota")
        self.btn_limpar.setIcon(IconFactory.limpar())
        self.btn_limpar.setStyleSheet("""
            QPushButton { background-color: transparent; border: 1px solid #565b5e; color: #DCE4EE; }
            QPushButton:hover { background-color: #363a40; border-color: #7b8387; color: white; }
            QPushButton:pressed { background-color: #1e1e1e; }
        """)
        self.btn_limpar.clicked.connect(self.limpar_rota)
        layout_sidebar.addWidget(self.btn_limpar)

        # ── SEÇÃO: Ferramentas ──
        layout_sidebar.addWidget(self._criar_separador())
        lbl_tools = QLabel("FERRAMENTAS")
        lbl_tools.setStyleSheet("color: #808080; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout_sidebar.addWidget(lbl_tools)

        self.btn_edicao = QPushButton("Ativar Modo Edição")
        self.btn_edicao.setIcon(IconFactory.edicao())
        self.btn_edicao.setCheckable(True)
        self.btn_edicao.setStyleSheet("""
            QPushButton { background-color: #bf616a; color: white; }
            QPushButton:hover { background-color: #d66f78; }
            QPushButton:checked { background-color: #a3be8c; color: white; font-weight: bold; }
        """)
        self.btn_edicao.toggled.connect(self.alternar_modo_edicao)
        layout_sidebar.addWidget(self.btn_edicao)

        self.btn_rotulos = QPushButton("Exibir Rótulos")
        self.btn_rotulos.setIcon(IconFactory.rotulos())
        self.btn_rotulos.setCheckable(True)
        self.btn_rotulos.setStyleSheet("""
            QPushButton { background-color: #434c5e; color: white; }
            QPushButton:hover { background-color: #515c72; }
            QPushButton:checked { background-color: #88c0d0; color: #2b2b2b; font-weight: bold; }
        """)
        self.btn_rotulos.toggled.connect(self.alternar_rotulos)
        layout_sidebar.addWidget(self.btn_rotulos)

        # ── SEÇÃO: Exportação ──
        layout_sidebar.addWidget(self._criar_separador())
        lbl_export = QLabel("EXPORTAÇÃO")
        lbl_export.setStyleSheet("color: #808080; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout_sidebar.addWidget(lbl_export)

        self.btn_copiar = QPushButton("Copiar Imagem")
        self.btn_copiar.setIcon(IconFactory.copiar())
        self.btn_copiar.setStyleSheet("""
            QPushButton { background-color: #4c566a; color: white; }
            QPushButton:hover { background-color: #5e6982; }
            QPushButton:pressed { background-color: #3b4352; }
        """)
        self.btn_copiar.clicked.connect(self.copiar_imagem)
        layout_sidebar.addWidget(self.btn_copiar)

        layout_sidebar.addStretch()

        # Painel de Estatísticas
        frame_stats = QFrame()
        frame_stats.setObjectName("StatsCard")
        frame_stats.setStyleSheet("""
            QFrame#StatsCard { background-color: #232323; border-radius: 8px; border: none; }
            QLabel { font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 11px; color: #a0a0a0; border: none; }
        """)
        layout_stats = QVBoxLayout(frame_stats)
        layout_stats.setContentsMargins(15, 15, 15, 15)
        layout_stats.setSpacing(8)

        lbl_stats_title = QLabel("Informações do Grafo")
        lbl_stats_title.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-weight: bold; color: #DCE4EE; font-size: 12px; margin-bottom: 5px; border: none;")
        layout_stats.addWidget(lbl_stats_title)

        self.lbl_vertices_count = QLabel("Vértices: --")
        layout_stats.addWidget(self.lbl_vertices_count)

        self.lbl_arestas_count = QLabel("Arestas: --")
        layout_stats.addWidget(self.lbl_arestas_count)

        sep_stats = QFrame()
        sep_stats.setFrameShape(QFrame.Shape.HLine)
        sep_stats.setStyleSheet("background-color: #3b3b3b; border: none; max-height: 1px;")
        layout_stats.addWidget(sep_stats)

        self.lbl_tempo = QLabel("Tempo: -- ms")
        layout_stats.addWidget(self.lbl_tempo)

        self.lbl_nos = QLabel("Nós expl.: --")
        layout_stats.addWidget(self.lbl_nos)

        self.lbl_custo = QLabel("Distância: -- u.m.")
        layout_stats.addWidget(self.lbl_custo)

        layout_sidebar.addWidget(frame_stats)

        layout_principal.addWidget(sidebar)

        self.scene = QGraphicsScene()
        self.view = MapGraphicsView(self.scene, self)
        layout_principal.addWidget(self.view)

    def _criar_separador(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #3b3b3b; border: none; max-height: 1px;")
        return sep

    def mostrar_estado_vazio(self):
        self.scene.clear()
        titulo = self.scene.addSimpleText("Importe um mapa para começar", QFont("Segoe UI", 16))
        titulo.setBrush(QBrush(QColor("#4c566a")))
        titulo.setPos(-titulo.boundingRect().width() / 2, -20)
        sub = self.scene.addSimpleText("Clique em 'Importar Mapa' na barra lateral", QFont("Segoe UI", 10))
        sub.setBrush(QBrush(QColor("#3b4252")))
        sub.setPos(-sub.boundingRect().width() / 2, 15)
        QTimer.singleShot(50, lambda: self.view.fitInView(
            self.scene.itemsBoundingRect().adjusted(-100, -50, 100, 50),
            Qt.AspectRatioMode.KeepAspectRatio
        ))

    def importar_mapa(self):
        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Mapa",
            str(Path.home()),
            "Mapas (*.poly *.osm *.xml *.txt);;Todos os Arquivos (*)"
        )
        if arquivo:
            self.caminho_mapa_original = arquivo
            self.carregar_e_desenhar_mapa()
            nome = Path(arquivo).name
            self.lbl_mapa_atual.setText(nome)
            self.lbl_mapa_atual.setStyleSheet("color: #a3be8c; font-size: 10px; font-style: normal; border: none; padding-left: 2px;")
            self.btn_remover.show()
            self.btn_edicao.setChecked(False)
            self.notification.show_message(f"Mapa '{nome}' importado!", sucesso=True)

    def remover_mapa(self):
        self.caminho_mapa_original = None
        self.vertices = {}
        self.todas_arestas = []
        self.limpar_rota()
        self.lbl_mapa_atual.setText("Nenhum mapa carregado")
        self.lbl_mapa_atual.setStyleSheet("color: #606060; font-size: 10px; font-style: italic; border: none; padding-left: 2px;")
        self.btn_remover.hide()
        self.lbl_vertices_count.setText("Vértices: --")
        self.lbl_arestas_count.setText("Arestas: --")
        self.btn_edicao.setChecked(False)
        self.mostrar_estado_vazio()
        self.notification.show_message("Mapa removido.", sucesso=True)

    def carregar_e_desenhar_mapa(self):
        if not self.caminho_mapa_original:
            return

        mapa_path = Path(self.caminho_mapa_original)
        if not mapa_path.exists():
            self.notification.show_message("Erro: Arquivo não encontrado.", sucesso=False)
            return

        try:
            if mapa_path.suffix.lower() in ['.osm', '.xml']:
                self.vertices, self.todas_arestas = load_osm(mapa_path)
            else:
                self.vertices, self.todas_arestas = load_poly(mapa_path)
            self.lbl_vertices_count.setText(f"Vértices: {len(self.vertices):,}")
            self.lbl_arestas_count.setText(f"Arestas: {len(self.todas_arestas):,}")
            self.redesenhar_mapa_completo(reset_view=True)
        except Exception as e:
            self.notification.show_message(f"Erro ao carregar mapa: {e}", sucesso=False)
            print(f"Erro ao carregar mapa: {e}")

    def redesenhar_mapa_completo(self, reset_view=False):
        self.scene.clear()
        self.itens_rota.clear()
        self.labels.clear()
        self.origem = self.destino = None
        
        draw_map(self.scene, self.vertices, self.todas_arestas)
        
        # Otimização de Desempenho: Só cria as milhares de bolinhas azuis/tooltips se a opção estiver ligada
        if self.btn_rotulos.isChecked():
            self.labels = draw_labels(self.scene, self.vertices, self.todas_arestas)
            for lbl in self.labels:
                lbl.show()
                
        # No Modo Edição, desenhamos apenas os pontos que o usuário criou ou selecionou
        if self.modo_edicao_ativo:
            for vid in self.vertices_edicao:
                if vid in self.vertices:
                    self.desenhar_ponto(vid, "#b48ead") # Lilás para edição
            
        if reset_view:
            rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(rect.adjusted(-500, -500, 500, 500))
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def alternar_rotulos(self, ativo):
        if ativo:
            if not self.labels:
                self.labels = draw_labels(self.scene, self.vertices, self.todas_arestas)
            for lbl in self.labels:
                lbl.show()
        else:
            for lbl in self.labels:
                lbl.hide()

    def alternar_modo_edicao(self, ativo):
        self.modo_edicao_ativo = ativo
        self.vertices_edicao.clear() # Limpa a lista de visualização ao alternar
        if ativo:
            self.btn_edicao.setText("Desativar Modo Edição")
            self.limpar_rota()
            self.update_status("Modo edição ativado. Clique para criar ou conectar nós.")
        else:
            self.btn_edicao.setText("Ativar Modo Edição")
            self.no_edicao_selecionado = None
            self.update_status("Clique no mapa para definir origem e destino.")

    def update_status(self, mensagem: str, sucesso: bool = True):
        # Exibe popup apenas para encontrar rota ou não encontrar
        if "encontrada" in mensagem.lower() or "nenhum" in mensagem.lower():
            self.notification.show_message(mensagem, sucesso)

    def ao_clicar_mapa(self, x_clique, y_clique, shift_pressed=False):
        no_mais_proximo, menor_dist_sq = find_nearest_vertex(self.vertices, x_clique, y_clique)
        zoom = self.view.transform().m11()
        clicou_no_vazio = menor_dist_sq > (18 / zoom) ** 2

        if self.modo_edicao_ativo:
            if shift_pressed and not clicou_no_vazio:
                # Remover o vértice e todas as arestas conectadas a ele
                if no_mais_proximo in self.vertices:
                    del self.vertices[no_mais_proximo]
                self.todas_arestas = [
                    (u, v) for u, v in self.todas_arestas 
                    if u != no_mais_proximo and v != no_mais_proximo
                ]
                self.vertices_edicao.discard(no_mais_proximo)
                if self.no_edicao_selecionado == no_mais_proximo:
                    self.no_edicao_selecionado = None
                self.redesenhar_mapa_completo(reset_view=False)
                self.notification.show_message(f"Vértice {no_mais_proximo} removido.", sucesso=True)
                return

            if clicou_no_vazio:
                novo_id = create_vertex(self.vertices, x_clique, y_clique)
                self.vertices_edicao.add(novo_id)
                self.redesenhar_mapa_completo(reset_view=False)
                self.notification.show_message(f"Vértice {novo_id} criado. Clique nele para conectar.", sucesso=True)
            else:
                self.vertices_edicao.add(no_mais_proximo)
                if self.no_edicao_selecionado is None:
                    # Primeiro clique: selecionar para conexão (amarelo)
                    self.no_edicao_selecionado = no_mais_proximo
                    self.redesenhar_mapa_completo(reset_view=False)
                    self.desenhar_ponto(no_mais_proximo, "#f1c40f")  # Amarelo = selecionado
                    self.notification.show_message(f"Vértice {no_mais_proximo} selecionado. Clique em outro para conectar.", sucesso=True)
                elif self.no_edicao_selecionado == no_mais_proximo:
                    # Clicou no mesmo: desselecionar
                    self.no_edicao_selecionado = None
                    self.redesenhar_mapa_completo(reset_view=False)
                    self.notification.show_message("Seleção cancelada.", sucesso=True)
                else:
                    # Segundo clique: criar aresta
                    self.todas_arestas.append((self.no_edicao_selecionado, no_mais_proximo))
                    self.vertices_edicao.add(self.no_edicao_selecionado)
                    self.no_edicao_selecionado = None
                    self.redesenhar_mapa_completo(reset_view=False)
                    self.notification.show_message("Aresta criada!", sucesso=True)
            return

        if not clicou_no_vazio:
            if self.origem is None:
                self.limpar_rota()
                self.origem = no_mais_proximo
                self.desenhar_ponto(self.origem, "#ff4c4c")
                self.lbl_origem.setText(f"Origem: Vértice {self.origem}")
            elif self.destino is None and no_mais_proximo != self.origem:
                self.destino = no_mais_proximo
                self.desenhar_ponto(self.destino, "#50fa7b")
                self.lbl_destino.setText(f"Destino: Vértice {self.destino}")
            else:
                self.limpar_rota()
                self.origem = no_mais_proximo
                self.desenhar_ponto(self.origem, "#ff4c4c")
                self.lbl_origem.setText(f"Origem: Vértice {self.origem}")

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
            self.notification.show_message(f"Erro: {str(e)}", sucesso=False)
            print(f"Erro na integração: {e}")

    def limpar_rota(self):
        for item in self.itens_rota:
            if hasattr(item, 'stop_pulse'):
                item.stop_pulse()
            self.scene.removeItem(item)
        self.itens_rota.clear()
        self.origem = self.destino = None
        self.lbl_origem.setText("Origem: --")
        self.lbl_destino.setText("Destino: --")
        self.lbl_tempo.setText("Tempo: -- ms")
        self.lbl_nos.setText("Nós explorados: --")
        self.lbl_custo.setText("Distância: -- u.m.")

    def copiar_imagem(self):
        QApplication.clipboard().setPixmap(self.view.grab())
        self.notification.show_message("Imagem copiada para a área de transferência!", sucesso=True)
        print("Copiado!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MinRouteApp()
    win.show()
    sys.exit(app.exec())