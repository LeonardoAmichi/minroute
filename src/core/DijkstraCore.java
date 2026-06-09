package src.core;

import java.util.*;

/**
 * Esta é a classe principal de matemática do projeto!
 * É aqui que roda o Algoritmo de Dijkstra, responsável por encontrar o caminho mais rápido/curto
 * entre dois pontos no nosso mapa (Grafo).
 */
public class DijkstraCore {

    /**
     * O 'NoFila' é um ajudante que usamos para organizar a fila de pontos a visitar.
     * Ele guarda qual é o ponto (id) e qual é a distância estimada até ele no momento.
     */
    static class NoFila implements Comparable<NoFila> {
        int id;
        double distancia;

        public NoFila(int id, double distancia) {
            this.id = id;
            this.distancia = distancia;
        }

        // Essa função ensina a fila a se organizar: os pontos com menor distância ficam na frente!
        @Override
        public int compareTo(NoFila outro) {
            return Double.compare(this.distancia, outro.distancia);
        }
    }

    /**
     * Ponto de entrada do programa Java. O Python chama essa função passando os argumentos.
     */
    public static void main(String[] args) {
        // Se não nos derem o mapa, de onde sair e onde chegar, não temos o que fazer!
        if (args.length < 3) {
            System.err.println("{\"erro\": \"Ops! Forma de usar: java src.core.DijkstraCore <arquivo> <origem> <destino>\"}");
            System.exit(1);
        }

        try {
            // Vamos cronometrar para ver o quão rápidos somos
            long tempoInicio = System.currentTimeMillis();

            // 1. O Parser faz a leitura "suja" (decidindo qual o formato do mapa pela extensão)
            String caminhoArquivo = args[0];
            Grafo grafo;
            
            // Escolhemos o tradutor correto para o tipo de arquivo
            if (caminhoArquivo.toLowerCase().endsWith(".osm") || caminhoArquivo.toLowerCase().endsWith(".xml")) {
                grafo = ParserOSM.carregar(caminhoArquivo);
            } else if (caminhoArquivo.toLowerCase().endsWith(".txt")) {
                grafo = ParserTXT.parse(caminhoArquivo);
            } else {
                grafo = ParserPoly.carregar(caminhoArquivo);
            }
            
            // 2. Executa a matemática "limpa" para achar a rota
            int origem = Integer.parseInt(args[1]);
            int destino = Integer.parseInt(args[2]);
            ResultadoDijkstra resultado = executarDijkstra(grafo, origem, destino);

            // 3. Empacota a resposta no formato JSON para o Python conseguir ler
            long tempoProcessamento = System.currentTimeMillis() - tempoInicio;
            imprimirResultadoJSON(resultado, tempoProcessamento);

        } catch (Exception e) {
            // Se algo explodir, avisamos o Python com um JSON de erro
            System.err.println("{\"erro\": \"" + e.getMessage() + "\"}");
            System.exit(1);
        }
    }

    /**
     * O famoso Algoritmo de Dijkstra! Ele explora o mapa passo a passo até achar o melhor caminho.
     */
    private static ResultadoDijkstra executarDijkstra(Grafo grafo, int origem, int destino) {
        // 'distancias' guarda a menor distância que achamos do início até o ponto X
        double[] distancias = new double[grafo.totalVertices];
        // 'predecessores' funciona como um rastro de migalhas para sabermos por onde viemos
        int[] predecessores = new int[grafo.totalVertices];
        // 'visitados' nos ajuda a não andar em círculos
        boolean[] visitados = new boolean[grafo.totalVertices];
        
        // No começo, não sabemos a distância para ninguém, então chutamos "infinito"
        Arrays.fill(distancias, Double.POSITIVE_INFINITY);
        // E também não viemos de lugar nenhum, então enchemos de -1
        Arrays.fill(predecessores, -1);
        
        // A distância do ponto de partida até ele mesmo é, obviamente, zero!
        distancias[origem] = 0;
        
        // Fila de Prioridade (Heap Mínima): ela sempre nos entrega primeiro o ponto mais próximo.
        PriorityQueue<NoFila> filaPrioridade = new PriorityQueue<>();
        filaPrioridade.add(new NoFila(origem, 0.0));
        
        int nosExplorados = 0; // Para estatística: quantos cruzamentos olhamos?

        while (!filaPrioridade.isEmpty()) {
            // Pega o ponto mais próximo na fila
            NoFila atual = filaPrioridade.poll();
            int u = atual.id;

            // Se já passamos por aqui antes e já fizemos o que tínhamos que fazer, pula!
            if (visitados[u]) continue;
            visitados[u] = true;
            nosExplorados++;

            // Oba, chegamos no destino! Podemos parar a busca.
            if (u == destino) break;

            // Vamos olhar para onde dá para ir a partir do ponto atual (nossos vizinhos)
            if (grafo.vertices[u] != null) {
                for (Grafo.Aresta aresta : grafo.vertices[u].vizinhos) {
                    int v = aresta.destino;
                    double peso = aresta.peso;

                    // Se não visitamos o vizinho ainda E o caminho por aqui for mais rápido
                    // do que o melhor caminho que conhecíamos antes...
                    if (!visitados[v] && distancias[u] + peso < distancias[v]) {
                        // Atualizamos a distância! Achamos um atalho!
                        distancias[v] = distancias[u] + peso;
                        // Deixamos a migalha de pão dizendo "vim daqui"
                        predecessores[v] = u;
                        // E colocamos o vizinho na fila para ser explorado mais tarde
                        filaPrioridade.add(new NoFila(v, distancias[v]));
                    }
                }
            }
        }

        // Depois que terminamos de explorar, remontamos o caminho de trás pra frente
        return reconstruirCaminho(origem, destino, distancias, predecessores, nosExplorados);
    }

    /**
     * Usa as "migalhas de pão" (predecessores) para traçar o caminho do destino de volta para a origem.
     */
    private static ResultadoDijkstra reconstruirCaminho(int origem, int destino, double[] dist, int[] prev, int nosExplorados) {
        List<Integer> caminho = new ArrayList<>();
        
        // Se a distância ainda for "infinito", significa que é impossível chegar lá (não tem rua)
        if (dist[destino] == Double.POSITIVE_INFINITY) {
            return new ResultadoDijkstra(caminho, -1.0, nosExplorados);
        }

        // Vai voltando pelo rastro de migalhas...
        for (int at = destino; at != -1; at = prev[at]) {
            caminho.add(at);
        }
        // ...e depois inverte a lista para ficar na ordem certa (da origem pro destino)
        Collections.reverse(caminho);
        
        return new ResultadoDijkstra(caminho, dist[destino], nosExplorados);
    }

    /**
     * Pega o resultado da nossa matemática e formata como um texto bonitinho em JSON
     * que a interface feita em Python vai adorar ler.
     */
    private static void imprimirResultadoJSON(ResultadoDijkstra resultado, long tempoMs) {
        StringBuilder json = new StringBuilder();
        json.append("{\n");
        json.append("  \"tempo_ms\": ").append(tempoMs).append(",\n");
        json.append("  \"nos_explorados\": ").append(resultado.nosExplorados).append(",\n");
        json.append("  \"distancia_total\": ").append(resultado.distanciaTotal).append(",\n");
        json.append("  \"caminho\": [");
        
        // Monta a lista do caminho
        for (int i = 0; i < resultado.caminho.size(); i++) {
            json.append(resultado.caminho.get(i));
            if (i < resultado.caminho.size() - 1) json.append(", ");
        }
        
        json.append("]\n}");
        // Imprime a resposta na tela (que será capturada pelo Python)
        System.out.println(json.toString());
    }

    /**
     * Uma caixinha para guardarmos o resumo de tudo o que a busca de rota encontrou.
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