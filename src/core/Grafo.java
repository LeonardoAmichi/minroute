package src.core;

import java.util.ArrayList;
import java.util.List;

public class Grafo {
    
    public static class Aresta {
        public int destino;
        public double peso;

        public Aresta(int destino, double peso) {
            this.destino = destino;
            this.peso = peso;
        }
    }

    public static class Vertice {
        public long id;
        public double x, y;
        public List<Aresta> vizinhos;

        public Vertice(long id, double x, double y) {
            this.id = id;
            this.x = x;
            this.y = y;
            this.vizinhos = new ArrayList<>();
        }
    }

    public Vertice[] vertices;
    public int totalVertices;

    public Grafo(int totalVertices) {
        this.totalVertices = totalVertices;
        this.vertices = new Vertice[totalVertices];
    }

    public void adicionarVertice(int id, double x, double y) {
        vertices[id] = new Vertice(id, x, y);
    }

    public void adicionarArestaBidirecional(int origem, int destino) {
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return;
        }
        
        // Calcula a distância euclidiana automaticamente ao criar a aresta
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
        
        // RNF06: Suporte a mão dupla (adicionamos a volta também)
        vertices[destino].vizinhos.add(new Aresta(origem, peso));
    }

    public void adicionarArestaDirecionada(int origem, int destino) {
        if (origem >= vertices.length || destino >= vertices.length || 
            vertices[origem] == null || vertices[destino] == null) {
            return;
        }
        
        double peso = calcularDistancia(vertices[origem], vertices[destino]);
        vertices[origem].vizinhos.add(new Aresta(destino, peso));
    }

    private double calcularDistancia(Vertice v1, Vertice v2) {
        return Math.sqrt(Math.pow(v1.x - v2.x, 2) + Math.pow(v1.y - v2.y, 2));
    }
}