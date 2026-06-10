package src.core;

import java.util.ArrayList;
import java.util.List;

/**
 * Representa o grafo de mapas: vértices (pontos) conectados por arestas (ruas).
 */
public class Grafo {
    
    /**
     * Uma Aresta é como uma rua ou estrada que liga um ponto a outro.
     * Ela guarda para onde vai (destino) e qual o custo/distância para chegar lá (peso).
     */
    public static class Aresta {
        public int destino;
        public double peso;

        public Aresta(int destino, double peso) {
            this.destino = destino;
            this.peso = peso;
        }
    }

    /**
     * Vértice do grafo, com identificador, coordenadas e lista de arestas adjacentes.
     */
    public static class Vertice {
        public long id;
        public double x, y;
        public List<Aresta> vizinhos;

        public Vertice(long id, double x, double y) {
            this.id = id;
            this.x = x;
            this.y = y;
            // Inicializa lista de arestas adjacentes vazia
            this.vizinhos = new ArrayList<>();
        }
    }

    // Vetor de vértices do grafo
    public Vertice[] vertices;
    // Quantidade total de vértices alocada
    public int totalVertices;

    /**
     * Quando criamos um novo Grafo (mapa), precisamos dizer quantos pontos ele terá.
     */
    public Grafo(int totalVertices) {
        this.totalVertices = totalVertices;
        this.vertices = new Vertice[totalVertices];
    }

    /**
     * Adiciona um novo ponto (vértice) no nosso mapa, passando seu ID e onde ele fica (x, y).
     */
    public void adicionarVertice(int id, double x, double y) {
        vertices[id] = new Vertice(id, x, y);
    }

    /**
     * Cria uma rua de mão dupla entre dois pontos. Ou seja, você pode ir e voltar por ela.
     */
    public void adicionarArestaBidirecional(int origem, int destino) {
        // Valida índices e existência dos vértices
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return; // Ignora aresta se algum vértice for inválido
        }
        
        // Calcula o peso (distância euclidiana) entre os vértices
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        
        // Adiciona aresta de ida
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
        
        // Adiciona aresta de volta (bidirecional)
        vertices[destino].vizinhos.add(new Aresta(origem, peso));
    }

    /**
     * Cria uma rua de mão única. Você só pode ir da origem para o destino.
     */
    public void adicionarArestaDirecionada(int origem, int destino) {
        // Valida índices e existência dos vértices
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return;
        }
        
        // Calcula o peso (distância euclidiana)
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        
        // Adiciona aresta direcionada (origem -> destino)
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
    }

    /**
     * Calcula a distância euclidiana entre dois vértices.
     */
    private double calcularDistancia(Vertice v1, Vertice v2) {
        // Distância euclidiana (raiz de soma dos quadrados das diferenças)
        return Math.sqrt(Math.pow(v1.x - v2.x, 2) + Math.pow(v1.y - v2.y, 2));
    }
}