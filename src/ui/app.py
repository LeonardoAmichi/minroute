import customtkinter as ctk
import tkinter as tk
import os
import subprocess
import json

# Configuração da aparência minimalista
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NavGraphApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NavGraph - Sistema de Navegação")
        self.geometry("1100x700")
        
        # O NOME EXATO DO ARQUIVO (Case Sensitive no Linux)
        self.caminho_mapa = "data/Campus2UFG&Regiao.poly"
        
        self.vertices = {}
        self.arestas_lidas = []
        self.coordenadas_tela = {}
        
        # Zoom do mapa
        self.zoom = 1.0
        self.zoom_step = 1.1
        self.zoom_min = 0.4
        self.zoom_max = 4.0
        self.base_margin = 40

        # Variáveis de seleção (RF03)
        self.origem = None
        self.destino = None
        self.caminho_atual = []
        self.ids_elementos_rota = [] # Guarda os IDs das linhas desenhadas para poder apagar depois

        self.configurar_layout()
        self.carregar_e_desenhar_mapa()
        
        # Evento de clique do mouse no mapa (RF05 parcial)
        self.canvas.bind("<Button-1>", self.ao_clicar_mapa)

    def configurar_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ================= Sidebar (Painel de Controle) =================
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="NavGraph", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=(20, 30))

        self.btn_tracar = ctk.CTkButton(self.sidebar_frame, text="Traçar Menor Caminho", command=self.tracar_caminho)
        self.btn_tracar.pack(pady=10, padx=20, fill="x")

        self.btn_limpar = ctk.CTkButton(self.sidebar_frame, text="Limpar Rota", fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"), command=self.limpar_rota)
        self.btn_limpar.pack(pady=10, padx=20, fill="x")

        # Painel de Estatísticas (RF07)
        self.lbl_stats_titulo = ctk.CTkLabel(self.sidebar_frame, text="Estatísticas da Execução:", anchor="w")
        self.lbl_stats_titulo.pack(pady=(40, 5), padx=20, fill="x")
        
        fonte_stats = ctk.CTkFont(family="JetBrains Mono", size=12)
        
        self.lbl_tempo = ctk.CTkLabel(self.sidebar_frame, text="Tempo: -- ms", font=fonte_stats, anchor="w", text_color="gray60")
        self.lbl_tempo.pack(pady=2, padx=20, fill="x")
        
        self.lbl_nos = ctk.CTkLabel(self.sidebar_frame, text="Nós explorados: --", font=fonte_stats, anchor="w", text_color="gray60")
        self.lbl_nos.pack(pady=2, padx=20, fill="x")
        
        self.lbl_custo = ctk.CTkLabel(self.sidebar_frame, text="Distância: -- u.m.", font=fonte_stats, anchor="w", text_color="gray60")
        self.lbl_custo.pack(pady=2, padx=20, fill="x")

        # ================= Área do Mapa (Canvas) =================
        self.mapa_frame = ctk.CTkFrame(self, corner_radius=0)
        self.mapa_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.mapa_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
        self.canvas.bind("<Control-Button-4>", self.on_zoom)
        self.canvas.bind("<Control-Button-5>", self.on_zoom)
        self.bind_all("<Control-KeyPress>", self.on_ctrl_key)

    def carregar_e_desenhar_mapa(self):
        if not os.path.exists(self.caminho_mapa):
            print(f"Erro fatal: O arquivo {self.caminho_mapa} não foi encontrado na raiz do projeto.")
            return

        try:
            with open(self.caminho_mapa, 'r') as f:
                linha_cabecalho = f.readline().split()
                total_vertices = int(linha_cabecalho[0])
                
                for _ in range(total_vertices):
                    partes = f.readline().split()
                    id_no = int(partes[0])
                    x = float(partes[1].replace(',', '.'))
                    y = float(partes[2].replace(',', '.'))
                    self.vertices[id_no] = (x, y)

                linha_arestas = f.readline().split()
                total_arestas = int(linha_arestas[0])
                
                for _ in range(total_arestas):
                    partes = f.readline().split()
                    self.arestas_lidas.append((int(partes[1]), int(partes[2])))

            self.atualizar_transformacao()
            self.redesenhar_mapa()
            print("Mapa renderizado!")
            
        except Exception as e:
            print(f"Erro ao processar o mapa no Python: {e}")

    def atualizar_transformacao(self):
        if not self.vertices:
            return

        xs = [v[0] for v in self.vertices.values()]
        ys = [v[1] for v in self.vertices.values()]
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

        largura_mapa = max(self.max_x - self.min_x, 1)
        altura_mapa = max(self.max_y - self.min_y, 1)

        largura_canvas = 800 - (2 * self.base_margin)
        altura_canvas = 650 - (2 * self.base_margin)

        self.escala = min(largura_canvas / largura_mapa, altura_canvas / altura_mapa) * self.zoom
        self.coordenadas_tela.clear()

        for id_no, (x, y) in self.vertices.items():
            cx = self.base_margin + (x - self.min_x) * self.escala
            cy = self.base_margin + (y - self.min_y) * self.escala
            self.coordenadas_tela[id_no] = (cx, cy)

    def redesenhar_mapa(self):
        self.canvas.delete("all")
        self.ids_elementos_rota.clear()

        for origem, destino in self.arestas_lidas:
            x1, y1 = self.coordenadas_tela[origem]
            x2, y2 = self.coordenadas_tela[destino]
            self.canvas.create_line(x1, y1, x2, y2, fill="#4c566a", width=1)

        if self.origem is not None:
            self.desenhar_ponto(self.origem, "red")

        if self.destino is not None:
            self.desenhar_ponto(self.destino, "green")

        if self.caminho_atual:
            for i in range(len(self.caminho_atual) - 1):
                id_atual = self.caminho_atual[i]
                id_prox = self.caminho_atual[i + 1]
                x1, y1 = self.coordenadas_tela[id_atual]
                x2, y2 = self.coordenadas_tela[id_prox]
                linha = self.canvas.create_line(x1, y1, x2, y2, fill="#ebcb8b", width=3)
                self.ids_elementos_rota.append(linha)

    def on_zoom(self, event):
        if hasattr(event, 'delta'):
            zoom_in = event.delta > 0
        elif hasattr(event, 'num'):
            zoom_in = event.num == 4
        else:
            return

        self.alterar_zoom(zoom_in)

    def on_ctrl_key(self, event):
        if event.keysym in ("plus", "equal"):
            self.alterar_zoom(True)
        elif event.keysym in ("minus", "underscore"):
            self.alterar_zoom(False)

    def alterar_zoom(self, zoom_in):
        fator = self.zoom_step if zoom_in else 1 / self.zoom_step
        novo_zoom = max(self.zoom_min, min(self.zoom_max, self.zoom * fator))
        if abs(novo_zoom - self.zoom) < 1e-6:
            return

        self.zoom = novo_zoom
        self.atualizar_transformacao()
        self.redesenhar_mapa()

    def ao_clicar_mapa(self, event):
        x_clique, y_clique = event.x, event.y
        
        # Encontrar o vértice mais próximo do clique
        no_mais_proximo = None
        menor_dist = float('inf')
        
        for id_no, (cx, cy) in self.coordenadas_tela.items():
            dist = (cx - x_clique)**2 + (cy - y_clique)**2
            if dist < menor_dist:
                menor_dist = dist
                no_mais_proximo = id_no
                
        # Se o clique for muito longe de qualquer ponto (raio de ~15 pixels), ignora
        if menor_dist > 225: return 
        
        # Lógica de seleção Origem -> Destino (RF03)
        if self.origem is None:
            self.limpar_rota()
            self.origem = no_mais_proximo
            self.desenhar_ponto(self.origem, "red")
            print(f"Origem definida: {self.origem}")
            
        elif self.destino is None and no_mais_proximo != self.origem:
            self.destino = no_mais_proximo
            self.desenhar_ponto(self.destino, "green")
            print(f"Destino definido: {self.destino}")
            
        else:
            # Se já tinha os dois, recomeça a seleção
            self.limpar_rota()
            self.origem = no_mais_proximo
            self.desenhar_ponto(self.origem, "red")
            print(f"Origem redefinida: {self.origem}")

    def desenhar_ponto(self, id_no, cor):
        cx, cy = self.coordenadas_tela[id_no]
        raio = 5
        ponto = self.canvas.create_oval(cx-raio, cy-raio, cx+raio, cy+raio, fill=cor, outline="white")
        self.ids_elementos_rota.append(ponto)

    def tracar_caminho(self):
        if self.origem is None or self.destino is None:
            print("Por favor, selecione a Origem e o Destino clicando no mapa.")
            return
            
        print(f"Solicitando cálculo ao Java (Origem: {self.origem} -> Destino: {self.destino})...")
        
        try:
            # Caminho absoluto ao build do Java para evitar ClassNotFoundException
            projeto_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            java_classpath = os.path.join(projeto_root, "build", "classes")
            caminho_mapa_absoluto = os.path.join(projeto_root, self.caminho_mapa)

            # Integração Python -> Java via Subprocess
            comando = [
                "java",
                "-cp",
                java_classpath,
                "src.core.DijkstraCore",
                caminho_mapa_absoluto,
                str(self.origem),
                str(self.destino)
            ]
            resultado = subprocess.run(comando, capture_output=True, text=True)
            
            # Lê o JSON impresso pelo Java
            dados = json.loads(resultado.stdout)
            
            caminho = dados.get('caminho', [])
            if not caminho or dados.get('distancia_total') == -1:
                print("Não existe caminho entre estes dois pontos.")
                return

            self.caminho_atual = caminho
            self.redesenhar_mapa()

            # Atualizar as estatísticas na Sidebar (RF07)
            self.lbl_tempo.configure(text=f"Tempo: {dados['tempo_ms']} ms")
            self.lbl_nos.configure(text=f"Nós explorados: {dados['nos_explorados']}")
            self.lbl_custo.configure(text=f"Distância: {dados['distancia_total']:.2f} u.m.")
            
        except json.JSONDecodeError:
            print(f"Erro ao interpretar resposta do Java. Saída bruta: {resultado.stdout}\nErros: {resultado.stderr}")
        except Exception as e:
            print(f"Erro na execução do processo Java: {e}")

    def limpar_rota(self):
        for elemento in self.ids_elementos_rota:
            self.canvas.delete(elemento)
        self.ids_elementos_rota.clear()
        self.origem = None
        self.destino = None
        self.caminho_atual = []
        self.lbl_tempo.configure(text="Tempo: -- ms")
        self.lbl_nos.configure(text="Nós explorados: --")
        self.lbl_custo.configure(text="Distância: -- u.m.")
        self.redesenhar_mapa()

if __name__ == "__main__":
    app = NavGraphApp()
    app.mainloop()