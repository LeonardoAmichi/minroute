import java.io.*;
import java.util.*;

public class DijkstraCore {

    // Estrutura para representar as arestas (Lista de Adjacência)
    static class Aresta {
        int destino;
        double peso;

        public Aresta(int destino, double peso) {
            this.destino = destino;
            this.peso = peso;
        }
    }

    // Estrutura para representar os vértices
    static class Vertice {
        int id;
        double x, y;
        List<Aresta> vizinhos;

        public Vertice(int id, double x, double y) {
            this.id = id;
            this.x = x;
            this.y = y;
            this.vizinhos = new ArrayList<>();
        }
    }

    // Estrutura auxiliar para a Fila de Prioridade (Heap Mínima)
    static class NoFila implements Comparable<NoFila> {
        int id;
        double distancia;

        public NoFila(int id, double distancia) {
            this.id = id;
            this.distancia = distancia;
        }

        @Override
        public int compareTo(NoFila outro) {
            return Double.compare(this.distancia, outro.distancia);
        }
    }

    private static Vertice[] grafo;
    private static int totalVertices;

    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("Uso: java DijkstraCore <arquivo.poly> <origem> <destino>");
            System.exit(1);
        }

        String caminhoArquivo = args[0];
        int origem = Integer.parseInt(args[1]);
        int destino = Integer.parseInt(args[2]);

        long tempoInicio = System.currentTimeMillis();

        // 1. Carregar o Grafo (Simulação do Parser para o formato .poly)
        carregarGrafo(caminhoArquivo);

        // 2. Executar Dijkstra
        ResultadoDijkstra resultado = executarDijkstra(origem, destino);

        long tempoFim = System.currentTimeMillis();
        long tempoProcessamento = tempoFim - tempoInicio;

        // 3. Imprimir Saída em formato JSON para o Python ler via Subprocess
        imprimirResultadoJSON(resultado, tempoProcessamento);
    }

    private static void carregarGrafo(String caminhoArquivo) {
        // TODO: Implementar a leitura exata do formato .poly gerado pelo código em C.
        // O formato contém: total_nodes, coordenadas (id, x, y), total_edges e conexões (id, from, to).
        // Por enquanto, esta função é um "stub" (esqueleto) para receber a lógica de I/O.
    }

    private static ResultadoDijkstra executarDijkstra(int origem, int destino) {
        double[] distancias = new double[totalVertices];
        int[] predecessores = new int[totalVertices];
        boolean[] visitados = new boolean[totalVertices];
        
        Arrays.fill(distancias, Double.POSITIVE_INFINITY);
        Arrays.fill(predecessores, -1);
        
        distancias[origem] = 0;
        
        PriorityQueue<NoFila> filaPrioridade = new PriorityQueue<>();
        filaPrioridade.add(new NoFila(origem, 0.0));
        
        int nosExplorados = 0;

        while (!filaPrioridade.isEmpty()) {
            NoFila atual = filaPrioridade.poll();
            int u = atual.id;

            if (visitados[u]) continue;
            visitados[u] = true;
            nosExplorados++;

            if (u == destino) break; // Chegou ao destino, podemos parar

            if (grafo[u] != null) {
                for (Aresta aresta : grafo[u].vizinhos) {
                    int v = aresta.destino;
                    double peso = aresta.peso;

                    if (!visitados[v] && distancias[u] + peso < distancias[v]) {
                        distancias[v] = distancias[u] + peso;
                        predecessores[v] = u;
                        filaPrioridade.add(new NoFila(v, distancias[v]));
                    }
                }
            }
        }

        return reconstruirCaminho(origem, destino, distancias, predecessores, nosExplorados);
    }

    private static ResultadoDijkstra reconstruirCaminho(int origem, int destino, double[] dist, int[] prev, int nosExplorados) {
        List<Integer> caminho = new ArrayList<>();
        if (dist[destino] == Double.POSITIVE_INFINITY) {
            return new ResultadoDijkstra(caminho, -1.0, nosExplorados); // Sem caminho
        }

        for (int at = destino; at != -1; at = prev[at]) {
            caminho.add(at);
        }
        Collections.reverse(caminho);
        
        return new ResultadoDijkstra(caminho, dist[destino], nosExplorados);
    }

    private static void imprimirResultadoJSON(ResultadoDijkstra resultado, long tempoMs) {
        // Construção manual de um JSON simples para evitar dependências externas no .jar
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"tempo_ms\": ").append(tempoMs).append(",\n");
        json.append("  \"nos_explorados\": ").append(resultado.nosExplorados).append(",\n");
        json.append("  \"distancia_total\": ").append(resultado.distanciaTotal).append(",\n");
        json.append("  \"caminho\": [");
        
        for (int i = 0; i < resultado.caminho.size(); i++) {
            json.append(resultado.caminho.get(i));
            if (i < resultado.caminho.size() - 1) json.append(", ");
        }
        
        json.append("]\n}");
        System.out.println(json.toString());
    }

    static class ResultadoDijkstra {
        List<Integer> caminho;
        double distanciaTotal;
        int nosExplorados;

        public ResultadoDijkstra(List<Integer> caminho, double distanciaTotal, int nosExplorados) {
            this.caminho = caminho;
            this.distanciaTotal = distanciaTotal;
            this.nosExplorados = nosExplorados;
        }
    }
}