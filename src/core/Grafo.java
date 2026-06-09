package src.core;

import java.util.ArrayList;
import java.util.List;

/**
 * A classe Grafo representa o "mapa" que vamos usar para encontrar as rotas.
 * Pense nela como uma teia de pontos (vértices) interligados por caminhos (arestas).
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
     * Um Vértice é um cruzamento ou ponto de interesse no nosso mapa.
     * Cada ponto tem uma identificação (id), coordenadas no mapa (x e y) 
     * e uma lista de todos os caminhos que saem dele (vizinhos).
     */
    public static class Vertice {
        public long id;
        public double x, y;
        public List<Aresta> vizinhos;

        public Vertice(long id, double x, double y) {
            this.id = id;
            this.x = x;
            this.y = y;
            // Começamos com uma lista vazia de caminhos
            this.vizinhos = new ArrayList<>();
        }
    }

    // Aqui guardamos todos os pontos do nosso mapa
    public Vertice[] vertices;
    // E aqui anotamos quantos pontos existem no total
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
        // Primeiro, verificamos se os pontos realmente existem no mapa
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return; // Se não existirem, a gente apenas ignora
        }
        
        // Calcula a distância real entre os dois pontos de forma automática
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        
        // Cria o caminho de ida
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
        
        // RNF06: Suporte a mão dupla (criamos o caminho de volta também)
        vertices[destino].vizinhos.add(new Aresta(origem, peso));
    }

    /**
     * Cria uma rua de mão única. Você só pode ir da origem para o destino.
     */
    public void adicionarArestaDirecionada(int origem, int destino) {
        // Verifica novamente se os pontos são válidos
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return;
        }
        
        // Calcula a distância
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        
        // Adiciona apenas o caminho de ida, sem a volta
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
    }

    /**
     * Uma função auxiliar que descobre qual é a distância em linha reta (euclidiana)
     * entre dois pontos do mapa.
     */
    private double calcularDistancia(Vertice v1, Vertice v2) {
        // Usa o teorema de Pitágoras para achar a distância!
        return Math.sqrt(Math.pow(v1.x - v2.x, 2) + Math.pow(v1.y - v2.y, 2));
    }
}