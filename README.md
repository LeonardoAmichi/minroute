# MinRoute
Sistema de Navegação Primitivo baseado no Algoritmo de Dijkstra

MinRoute é um sistema de navegação e roteamento de alto desempenho que combina uma interface gráfica intuitiva em Python (PyQt6) com um núcleo de processamento matemático otimizado em Java. O projeto utiliza o algoritmo de Dijkstra com uma Heap Mínima para calcular as rotas mais curtas em grafos gerados a partir de dados geográficos reais.

## Arquitetura Híbrida

O projeto adota uma arquitetura em dois processos (IPC) para maximizar a eficiência de cálculo e a experiência visual do usuário:

1. **Front-end (Python/PyQt6):** Camada interativa responsável pela renderização (via `QGraphicsScene`), eventos de mouse e gerenciamento de estado da aplicação (`app.py`).
2. **Back-end (Java):** Motor algorítmico (`DijkstraCore.java`) que estrutura a malha viária em um Array de Vértices para manter a memória esparsa em `O(V + E)`. Opera o Dijkstra de forma ultra-rápida resolvendo grafos em tempo sub-linear `O(E log V)`.
3. **Integração IPC (JSON Bridge):** O módulo utilitário `java_bridge.py` invoca a Java Virtual Machine (JVM), processa possíveis erros nativos da JVM e recebe o menor caminho perfeitamente de volta pelo STDOUT estruturado em JSON.

## Funcionalidades Principais

- **Suporte a múltiplos formatos:** OpenStreetMap (.osm), polígonos em grade cartesiana (.poly) e matrizes de teste (.txt).
- **Roteamento instantâneo:** Cálculo abaixo de 2 segundos para malhas médias, com bloqueio rigoroso (anti ghost-route) impedindo a navegação na contramão de vias de sentido único.
- **Rótulos Interativos:** Exibição do ID dos vértices e Peso (distância física) das arestas conectadas via Menu Suspenso flutuante (Hover Tooltip).
- **Edição Dinâmica do Grafo:**
  - **Criar Nós:** Clique em uma área vazia do canvas (agora com blindagem de proximidade que impede nós duplicados na mesma coordenada).
  - **Criar Vias:** Selecione origem e destino sucessivamente, definindo como via direcional ou bidirecional. O visual da aresta se adapta desenhando setas proporcionais dinamicamente.
  - **Remover Nós:** Duplo clique rápido sobre um vértice isola e destrói ele e todas as suas arestas conectadas.
- **Estatísticas On-Screen:** Controle de nós explorados, tempo de processamento em ms e custo final da rota (distância total).
- **Exportação Fácil:** Recurso embutido para capturar e jogar a visão do grafo diretamente para a Área de Transferência.

## Estrutura de Diretórios

```text
minroute/
├── docs/               # Especificação técnica formal e PDF
├── data/               # Arquivos de mapas base (.poly, .osm) (gerenciado dinamicamente)
├── src/
│   ├── core/           # Código-fonte Java (Abstração do Grafo, Parsers e Dijkstra)
│   ├── ui/             # Código-fonte Python (Views, Renderização e Controllers)
│   └── utils/          # Módulos de lógica vetorial e integração IPC
├── build/              # Binários .class compilados do núcleo Java
└── README.md
```

## Guia Rápido de Execução Nativa

### Pré-requisitos
- Java Development Kit (JDK) 11 ou superior.
- Python 3.8+ instalado localmente.
- Ambiente operacional Windows ou Linux.

### Passos de Instalação e Execução

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/LeonardoAmichi/minroute.git
   cd minroute
   ```

2. **Instale as dependências visuais do Python:**
   ```bash
   pip install PyQt6
   ```

3. **Compile os binários do motor de busca Java:**
   Na raiz do projeto, garanta que os `.class` existam no diretório build:
   ```bash
    javac --release 11 -d build/classes src/core/*.java
   ```

4. **Inicie o Sistema:**
   ```bash
   python src/ui/app.py
   ```

*(Alternativa Autônoma)*: O projeto disponibiliza a pasta empacotada `dist/MinRoute/` contendo o `MinRoute.exe` com JRE portátil embutido, dispensando a instalação de Java e Python na máquina de destino.

## Licença e Autoria
Projeto estruturado de uso avaliativo da disciplina de Algoritmos e Estruturas de Dados 2 (AED2). Consulte a pasta `docs/` para acessar a base UML e especificações de Engenharia de Software.
