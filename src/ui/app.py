import sys
from pathlib import Path
import tempfile

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGraphicsScene, 
                             QFrame, QFileDialog, QCheckBox)
from PyQt6.QtGui import QColor, QBrush, QFont, QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer



if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys._MEIPASS) / "src"
else:
    ROOT_DIR = Path(__file__).resolve().parents[1]
    
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.map_model import create_vertex, find_nearest_vertex, load_poly, load_osm, load_txt, save_snapshot
from utils.java_bridge import run_dijkstra
from ui.renderer import (MapGraphicsView, draw_map, draw_point, draw_route, draw_labels)
from ui.icons import IconFactory


class NotificationWidget(QWidget):
    """
    Widget flutuante para exibir notificações breves (sucesso/erro) com animação.
    """
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
        
        # Centraliza horizontalmente no topo da janela
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
    """
    O Coração da Aplicação Visual! 
    É aqui que juntamos todas as peças: a barra lateral com os botões, 
    o mapa interativo no centro, e todas as ações que o usuário pode fazer.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MinRoute - Sistema de Navegação (Motor Qt)")
        self.resize(1100, 700)

        self.caminho_mapa_original = None
        self.caminho_mapa_editado = Path(tempfile.gettempdir()) / "minroute_mapa_editado.poly"

        self.vertices = {}
        self.todas_arestas = []

        self.origem = None
        self.destino = None
        self.itens_rota = []
        self.labels = []
        self.setas = []
        self.setas_rota = []
        self.modo_edicao_ativo = False
        self.no_edicao_selecionado = None

        self.vertices_edicao = set()  # Vértices criados ou selecionados na edição atual
        
        self.configurar_layout()
        self.notification = NotificationWidget(self.view)
        self.mostrar_estado_vazio()

        # Atalho: Ctrl+C para traçar o menor caminho
        atalho_tracar = QShortcut(QKeySequence("Ctrl+C"), self)
        atalho_tracar.activated.connect(self.tracar_caminho)

        # Atalhos de zoom (Ctrl+ e Ctrl-)
        atalho_zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        atalho_zoom_in.activated.connect(lambda: self.view.scale(1.15, 1.15))
        
        atalho_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        atalho_zoom_in_alt.activated.connect(lambda: self.view.scale(1.15, 1.15))

        atalho_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        atalho_zoom_out.activated.connect(lambda: self.view.scale(1 / 1.15, 1 / 1.15))

    def configurar_layout(self):
        """
        Constrói a interface principal: sidebar, botões e área de mapa.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QHBoxLayout(central_widget)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # Área lateral (sidebar)
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

        # Cabeçalho / logo
        lbl_logo = QLabel("MinRoute")
        lbl_logo.setFont(QFont("Segoe UI", 18, QFont.Weight.ExtraBold))
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("margin-bottom: 10px; border: none;")
        layout_sidebar.addWidget(lbl_logo)

        # Seção: Dados do Mapa
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

        # Seção: Navegação
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

        # Seção: Ferramentas
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

        self.btn_sentido = QPushButton("Exibir Sentido")
        self.btn_sentido.setIcon(IconFactory.sentido())
        self.btn_sentido.setCheckable(True)
        self.btn_sentido.setStyleSheet("""
            QPushButton { background-color: #434c5e; color: white; }
            QPushButton:hover { background-color: #515c72; }
            QPushButton:checked { background-color: #e5c07b; color: #2b2b2b; font-weight: bold; }
        """)
        self.btn_sentido.toggled.connect(self.alternar_sentido)
        layout_sidebar.addWidget(self.btn_sentido)

        self.cb_mao_unica = QCheckBox("Criar Via de Mão Única")
        self.cb_mao_unica.setStyleSheet("""
            QCheckBox { color: #DCE4EE; font-size: 12px; margin-top: 5px; border: none; }
            QCheckBox::indicator { width: 14px; height: 14px; }
        """)
        self.cb_mao_unica.hide()
        self.cb_mao_unica.toggled.connect(self.ao_alternar_mao_unica)
        layout_sidebar.addWidget(self.cb_mao_unica)

        # Seção: Exportação
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

        # Painel de estatísticas
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
        self.view.zoom_changed.connect(self.atualizar_tamanho_setas)
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
        """
        Abre a janelinha do Windows para o usuário escolher o arquivo do mapa.
        Se ele escolher, já tentamos desenhar na tela!
        """
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
        """
        Identifica o tipo de mapa (.poly, .osm, .txt) e usa as ferramentas 
        adequadas para ler o arquivo e desenhá-lo na tela.
        """
        if not self.caminho_mapa_original:
            return

        mapa_path = Path(self.caminho_mapa_original)
        if not mapa_path.exists():
            self.notification.show_message("Erro: Arquivo não encontrado.", sucesso=False)
            return

        try:
            if mapa_path.suffix.lower() in ['.osm', '.xml']:
                self.vertices, self.todas_arestas = load_osm(mapa_path)
            elif mapa_path.suffix.lower() == '.txt':
                self.vertices, self.todas_arestas = load_txt(mapa_path)
            else:
                self.vertices, self.todas_arestas = load_poly(mapa_path)
            self.lbl_vertices_count.setText(f"Vértices: {len(self.vertices):,}")
            self.lbl_arestas_count.setText(f"Arestas: {len(self.todas_arestas):,}")
            self.redesenhar_mapa_completo(reset_view=True)
        except Exception as e:
            self.notification.show_message(f"Erro ao carregar mapa: {e}", sucesso=False)
            print(f"Erro ao carregar mapa: {e}")

    def redesenhar_mapa_completo(self, reset_view=False):
        # Preserva origem/destino ao redesenhar para não perder a seleção
        origem_temp = self.origem
        destino_temp = self.destino
        
        self.scene.clear()
        self.itens_rota.clear()
        self.labels.clear()
        self.setas.clear()
        
        # Restaura origem/destino
        self.origem = origem_temp
        self.destino = destino_temp
        
        self.setas = draw_map(self.scene, self.vertices, self.todas_arestas)
        
        # draw_map retorna setas visíveis por padrão; oculta-as se a opção estiver desativada
        if not self.btn_sentido.isChecked():
            for seta in self.setas:
                seta.hide()
                
        # Aplica LOD (level-of-detail) às setas conforme a escala atual
        self.atualizar_tamanho_setas(self.view.transform().m11())
        
        # Otimização: cria tooltips apenas quando a opção de rótulos estiver habilitada
        if self.btn_rotulos.isChecked():
            self.labels = draw_labels(self.scene, self.vertices, self.todas_arestas)
            for lbl in self.labels:
                lbl.show()
                
        # No modo edição, desenha apenas os vértices criados ou selecionados pelo usuário
        if self.modo_edicao_ativo:
            for vid in self.vertices_edicao:
                if vid in self.vertices:
                    self.desenhar_ponto(vid, "#b48ead") # Cor de destaque para pontos em edição
                    
        # Redesenha origem e destino caso ainda existam no grafo
        if self.origem is not None:
            if self.origem in self.vertices:
                self.desenhar_ponto(self.origem, "#ff4c4c")
            else:
                self.origem = None
                self.lbl_origem.setText("Origem: --")

        if self.destino is not None:
            if self.destino in self.vertices:
                self.desenhar_ponto(self.destino, "#50fa7b")
            else:
                self.destino = None
                self.lbl_destino.setText("Destino: --")
            
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

    def alternar_sentido(self, ativo):
        """Liga ou desliga a exibição das setas de sentido (mapa + rota)."""
        if ativo:
            for seta in self.setas:
                seta.show()
            for seta in self.setas_rota:
                seta.show()
        else:
            for seta in self.setas:
                seta.hide()
            for seta in self.setas_rota:
                seta.hide()

    def atualizar_tamanho_setas(self, view_scale: float):
        """
        Level of Detail (LOD) dinâmico para as setas cosméticas:
        Ao afastar o zoom (zoom out), as arestas ficam minúsculas na tela.
        Se a seta continuasse com 8 pixels fixos, o mapa viraria um borrão (clutter).
        Aqui nós encolhemos as setas para que nunca excedam proporção da aresta visível.
        """
        for seta in self.setas:
            dist = seta.data(0)
            if dist:
                # view_scale * dist = tamanho da aresta em pixels na tela
                # 0.025 é um fator empírico para limitar o tamanho relativo da seta
                escala = min(1.0, dist * view_scale * 0.025)
                # Limite inferior evita transformação inválida na matriz do Qt
                seta.setScale(max(0.15, escala))

    def ao_alternar_mao_unica(self, checked):
        if checked and not self.btn_sentido.isChecked():
            self.btn_sentido.setChecked(True)

    def alternar_modo_edicao(self, ativo):
        self.modo_edicao_ativo = ativo
        self.vertices_edicao.clear() # Limpa seleção de vértices de edição ao alternar o modo
        if ativo:
            self.btn_edicao.setText("Desativar Modo Edição")
            self.limpar_rota()
            self.update_status("Modo edição ativado. Clique para criar ou conectar nós.")
            self.cb_mao_unica.show()
        else:
            self.btn_edicao.setText("Ativar Modo Edição")
            self.no_edicao_selecionado = None
            self.update_status("Clique no mapa para definir origem e destino.")
            self.cb_mao_unica.hide()

    def update_status(self, mensagem: str, sucesso: bool = True):
        # Mostra notificações relevantes relacionadas à operação de rota
        if "encontrada" in mensagem.lower() or "nenhum" in mensagem.lower():
            self.notification.show_message(mensagem, sucesso)

    def ao_duplo_clique_mapa(self, x_clique, y_clique):
        """
        Remove um vértice e as arestas conectadas em resposta a duplo clique no mapa
        (válido apenas no modo edição).
        """
        if not self.modo_edicao_ativo:
            return
            
        no_mais_proximo, menor_dist_sq = find_nearest_vertex(self.vertices, x_clique, y_clique)
        zoom = self.view.transform().m11()
        clicou_no_vazio = menor_dist_sq > (18 / zoom) ** 2
        
        if not clicou_no_vazio:
            # Remove vértice e todas as arestas associadas; atualiza seleção de edição
            if no_mais_proximo in self.vertices:
                del self.vertices[no_mais_proximo]
            self.todas_arestas = [
                edge for edge in self.todas_arestas 
                if edge[0] != no_mais_proximo and edge[1] != no_mais_proximo
            ]
            self.vertices_edicao.discard(no_mais_proximo)
            if self.no_edicao_selecionado == no_mais_proximo:
                self.no_edicao_selecionado = None
                
            self.redesenhar_mapa_completo(reset_view=False)
            self.notification.show_message(f"Vértice {no_mais_proximo} removido via duplo clique.", sucesso=True)

    def ao_clicar_mapa(self, x_clique, y_clique):
        no_mais_proximo, menor_dist_sq = find_nearest_vertex(self.vertices, x_clique, y_clique)
        zoom = self.view.transform().m11()
        clicou_no_vazio = menor_dist_sq > (18 / zoom) ** 2

        if self.modo_edicao_ativo:
            if clicou_no_vazio:
                if menor_dist_sq < 1e-4:
                    self.notification.show_message("Não é possível colocar dois vértices no mesmo lugar.", sucesso=False)
                    return
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
                    self.desenhar_ponto(no_mais_proximo, "#f1c40f")  # Indicador de seleção
                    self.notification.show_message(f"Vértice {no_mais_proximo} selecionado. Clique em outro para conectar.", sucesso=True)
                elif self.no_edicao_selecionado == no_mais_proximo:
                    # Clique repetido: desseleciona
                    self.no_edicao_selecionado = None
                    self.redesenhar_mapa_completo(reset_view=False)
                    self.notification.show_message("Seleção cancelada.", sucesso=True)
                else:
                    # Segundo clique: cria aresta entre vértices selecionados
                    is_bidir = not self.cb_mao_unica.isChecked()
                    self.todas_arestas.append((self.no_edicao_selecionado, no_mais_proximo, is_bidir))
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

    def desenhar_ponto(self, id_no, cor):
        draw_point(self.scene, self.vertices, id_no, cor, self.itens_rota)

    def tracar_caminho(self):
        """
        Executa o fluxo para traçar rota: salva snapshot, invoca o motor Java (Dijkstra)
        e desenha o resultado retornado.
        """
        if self.origem is None or self.destino is None:
            return

        try:
            save_snapshot(Path(self.caminho_mapa_editado), self.vertices, self.todas_arestas)

            if getattr(sys, 'frozen', False):
                projeto_root = Path(sys._MEIPASS)
            else:
                projeto_root = Path(__file__).resolve().parents[2]
            java_cp = projeto_root / "build" / "classes"
            dados = run_dijkstra(java_cp, Path(self.caminho_mapa_editado), self.origem, self.destino)

            caminho = dados.get("caminho", [])

            if caminho:
                self.setas_rota = draw_route(self.scene, self.vertices, caminho, self.itens_rota)
                # Se a opção de exibir sentido estiver desligada, oculta as setas da rota
                if not self.btn_sentido.isChecked():
                    for seta in self.setas_rota:
                        seta.hide()
                self.lbl_tempo.setText(f"Tempo: {dados['tempo_ms']} ms")
                self.lbl_nos.setText(f"Nós explorados: {dados['nos_explorados']}")
                self.lbl_custo.setText(f"Distância: {dados['distancia_total']:.2f} u.m.")
                self.update_status("Rota encontrada com sucesso.")
            else:
                # Tenta calcular rota no sentido inverso para verificar bloqueios por mão única
                try:
                    dados_reverso = run_dijkstra(java_cp, Path(self.caminho_mapa_editado), self.destino, self.origem)
                    caminho_reverso = dados_reverso.get("caminho", [])
                except Exception:
                    caminho_reverso = []

                if caminho_reverso:
                    # Existe rota no sentido inverso: provável bloqueio por via(s) de mão única
                    self.notification.show_message(
                        "Caminho bloqueado por via(s) de mão única! Tente inverter origem e destino.",
                        sucesso=False
                    )
                else:
                    # Nenhuma das direções produziu rota: vértices desconectados
                    self.notification.show_message(
                        "Nenhum caminho possível entre os pontos selecionados.",
                        sucesso=False
                    )
        except Exception as e:
            self.update_status("Erro ao calcular rota. Veja o console para detalhes.", sucesso=False)
            self.notification.show_message(f"Erro: {str(e)}", sucesso=False)

    def limpar_rota(self):
        for item in self.itens_rota:
            if hasattr(item, 'stop_pulse'):
                item.stop_pulse()
            self.scene.removeItem(item)
        self.itens_rota.clear()
        self.setas_rota.clear()
        self.origem = self.destino = None
        self.lbl_origem.setText("Origem: --")
        self.lbl_destino.setText("Destino: --")
        self.lbl_tempo.setText("Tempo: -- ms")
        self.lbl_nos.setText("Nós explorados: --")
        self.lbl_custo.setText("Distância: -- u.m.")

    def copiar_imagem(self):
        QApplication.clipboard().setPixmap(self.view.grab())
        self.notification.show_message("Imagem copiada para a área de transferência!", sucesso=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MinRouteApp()
    win.show()
    sys.exit(app.exec())