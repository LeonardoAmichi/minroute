package src.core;

import java.util.*;

/**
 * Responsável pelo cálculo de rotas usando o algoritmo de Dijkstra.
 * Fornece um ponto de entrada para execução standalone e retorna o resultado em JSON.
 */
public class DijkstraCore {

    /**
     * Nó auxiliar para a fila de prioridade, contendo o identificador do vértice e
     * a distância estimada a partir da origem.
     */
    static class NoFila implements Comparable<NoFila> {
        int id;
        double distancia;

        public NoFila(int id, double distancia) {
            this.id = id;
            this.distancia = distancia;
        }

        // Compara nós por distância para ordenar a fila de prioridade (menor primeiro).
        @Override
        public int compareTo(NoFila outro) {
            return Double.compare(this.distancia, outro.distancia);
        }
    }

    /**
     * Ponto de entrada da aplicação Java.
     * Recebe os argumentos: <arquivo_do_mapa> <origem> <destino>.
     */
    public static void main(String[] args) {
        // Valida argumentos de entrada e exibe uso em caso de formato incorreto.
        if (args.length < 3) {
            System.err.println("{\"erro\": \"Ops! Forma de usar: java src.core.DijkstraCore <arquivo> <origem> <destino>\"}");
            System.exit(1);
        }

        try {
            // Mede o tempo total de processamento
            long tempoInicio = System.currentTimeMillis();

            // Determina o parser apropriado a partir da extensão do arquivo
            String caminhoArquivo = args[0];
            Grafo grafo;
            
            // Seleciona o leitor adequado para o formato do mapa
            if (caminhoArquivo.toLowerCase().endsWith(".osm") || caminhoArquivo.toLowerCase().endsWith(".xml")) {
                grafo = ParserOSM.carregar(caminhoArquivo);
            } else if (caminhoArquivo.toLowerCase().endsWith(".txt")) {
                grafo = ParserTXT.parse(caminhoArquivo);
            } else {
                grafo = ParserPoly.carregar(caminhoArquivo);
            }
            
            // Executa o algoritmo para calcular a rota entre origem e destino
            int origem = Integer.parseInt(args[1]);
            int destino = Integer.parseInt(args[2]);
            ResultadoDijkstra resultado = executarDijkstra(grafo, origem, destino);

            // Formata o resultado em JSON para o chamador (Python)
            long tempoProcessamento = System.currentTimeMillis() - tempoInicio;
            imprimirResultadoJSON(resultado, tempoProcessamento);

        } catch (Exception e) {
            // Em caso de erro, retorna um JSON descrevendo o problema ao chamador
            System.err.println("{\"erro\": \"" + e.getMessage() + "\"}");
            System.exit(1);
        }
    }

    /**
     * Implementação do algoritmo de Dijkstra para encontrar o caminho mínimo
     * entre `origem` e `destino` em um objeto `Grafo`.
     */
    private static ResultadoDijkstra executarDijkstra(Grafo grafo, int origem, int destino) {
        // Distância mínima conhecida da origem até cada vértice
        double[] distancias = new double[grafo.totalVertices];
        // Predecessor imediato de cada vértice para reconstrução do caminho
        int[] predecessores = new int[grafo.totalVertices];
        // Marca vértices já processados para evitar reprocessamento
        boolean[] visitados = new boolean[grafo.totalVertices];
        
        // Inicializa distâncias com infinito e predecessores com valor inválido
        Arrays.fill(distancias, Double.POSITIVE_INFINITY);
        Arrays.fill(predecessores, -1);
        
        // Distância da origem até si mesma é zero
        distancias[origem] = 0;

        // Fila de prioridade (min-heap) usada para selecionar o próximo vértice a explorar
        PriorityQueue<NoFila> filaPrioridade = new PriorityQueue<>();
        filaPrioridade.add(new NoFila(origem, 0.0));

        int nosExplorados = 0; // Contador de vértices processados (estatística)

        while (!filaPrioridade.isEmpty()) {
            // Remove o vértice com menor distância estimada da fila
            NoFila atual = filaPrioridade.poll();
            int u = atual.id;

            // Ignora vértices já finalizados
            if (visitados[u]) continue;
            visitados[u] = true;
            nosExplorados++;

            // Destino alcançado; interrompe a exploração
            if (u == destino) break;

            // Relaxa arestas: percorre vizinhos e atualiza distâncias quando apropriado
            if (grafo.vertices[u] != null) {
                for (Grafo.Aresta aresta : grafo.vertices[u].vizinhos) {
                    int v = aresta.destino;
                    double peso = aresta.peso;

                    // Se o caminho via `u` melhora a distância conhecida até `v`
                    if (!visitados[v] && distancias[u] + peso < distancias[v]) {
                        // Atualiza distância e predecessor, e agenda o vértice para exploração
                        distancias[v] = distancias[u] + peso;
                        predecessores[v] = u;
                        filaPrioridade.add(new NoFila(v, distancias[v]));
                    }
                }
            }
        }

        // Reconstrói o caminho a partir dos predecessores e retorna o resultado
        return reconstruirCaminho(origem, destino, distancias, predecessores, nosExplorados);
    }

    /**
     * Reconstrói o caminho do destino até a origem utilizando o vetor de predecessores
     * e retorna um objeto com o caminho, distância total e estatísticas.
     */
    private static ResultadoDijkstra reconstruirCaminho(int origem, int destino, double[] dist, int[] prev, int nosExplorados) {
        List<Integer> caminho = new ArrayList<>();
        
        // Se a distância for infinito, não existe caminho entre origem e destino
        if (dist[destino] == Double.POSITIVE_INFINITY) {
            return new ResultadoDijkstra(caminho, -1.0, nosExplorados);
        }

        // Percorre os predecessores do destino até a origem
        for (int at = destino; at != -1; at = prev[at]) {
            caminho.add(at);
        }
        // Inverte para obter a sequência da origem ao destino
        Collections.reverse(caminho);
        
        return new ResultadoDijkstra(caminho, dist[destino], nosExplorados);
    }

    /**
     * Formata o resultado da busca em JSON para o consumidor externo (ex.: a ponte Python).
     */
    private static void imprimirResultadoJSON(ResultadoDijkstra resultado, long tempoMs) {
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"tempo_ms\": ").append(tempoMs).append(",\n");
        json.append("  \"nos_explorados\": ").append(resultado.nosExplorados).append(",\n");
        json.append("  \"distancia_total\": ").append(resultado.distanciaTotal).append(",\n");
        json.append("  \"caminho\": [");
        
        // Monta o array de vértices representando o caminho
        for (int i = 0; i < resultado.caminho.size(); i++) {
            json.append(resultado.caminho.get(i));
            if (i < resultado.caminho.size() - 1) json.append(", ");
        }
        
        json.append("]\n}");
        // Imprime a resposta na tela (que será capturada pelo Python)
        System.out.println(json.toString());
    }

    /**
     * Estrutura de retorno que agrupa o caminho, a distância total e estatísticas da busca.
     */
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