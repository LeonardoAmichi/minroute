package src.core;

import java.util.*;

public class DijkstraCore {

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

    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("{\"erro\": \"Uso: java src.core.DijkstraCore <arquivo.poly> <origem> <destino>\"}");
            System.exit(1);
        }

        try {
            long tempoInicio = System.currentTimeMillis();

            // 1. O Parser faz a leitura suja (decidindo o formato pela extensão)
            String caminhoArquivo = args[0];
            Grafo grafo;
            
            if (caminhoArquivo.toLowerCase().endsWith(".osm")) {
                grafo = ParserOSM.carregar(caminhoArquivo);
            } else {
                grafo = ParserPoly.carregar(caminhoArquivo);
            }
            
            // 2. Executa a matemática limpa
            int origem = Integer.parseInt(args[1]);
            int destino = Integer.parseInt(args[2]);
            ResultadoDijkstra resultado = executarDijkstra(grafo, origem, destino);

            // 3. Responde para o Python
            long tempoProcessamento = System.currentTimeMillis() - tempoInicio;
            imprimirResultadoJSON(resultado, tempoProcessamento);

        } catch (Exception e) {
            System.err.println("{\"erro\": \"" + e.getMessage() + "\"}");
            System.exit(1);
        }
    }

    private static ResultadoDijkstra executarDijkstra(Grafo grafo, int origem, int destino) {
        double[] distancias = new double[grafo.totalVertices];
        int[] predecessores = new int[grafo.totalVertices];
        boolean[] visitados = new boolean[grafo.totalVertices];
        
        Arrays.fill(distancias, Double.POSITIVE_INFINITY);
        Arrays.fill(predecessores, -1);
        
        distancias[origem] = 0;
        
        // Fila de Prioridade (Heap Mínima) exigida pelo edital[cite: 1]
        PriorityQueue<NoFila> filaPrioridade = new PriorityQueue<>();
        filaPrioridade.add(new NoFila(origem, 0.0));
        
        int nosExplorados = 0;

        while (!filaPrioridade.isEmpty()) {
            NoFila atual = filaPrioridade.poll();
            int u = atual.id;

            if (visitados[u]) continue;
            visitados[u] = true;
            nosExplorados++;

            if (u == destino) break;

            if (grafo.vertices[u] != null) {
                for (Grafo.Aresta aresta : grafo.vertices[u].vizinhos) {
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
            return new ResultadoDijkstra(caminho, -1.0, nosExplorados);
        }

        for (int at = destino; at != -1; at = prev[at]) {
            caminho.add(at);
        }
        Collections.reverse(caminho);
        
        return new ResultadoDijkstra(caminho, dist[destino], nosExplorados);
    }

    private static void imprimirResultadoJSON(ResultadoDijkstra resultado, long tempoMs) {
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