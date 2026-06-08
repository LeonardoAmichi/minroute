package src.core;

import java.io.BufferedReader;
import java.io.FileReader;

public class ParserPoly {

    public static Grafo carregar(String caminhoArquivo) throws Exception {
        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            
            // Lê total de vértices
            String linha = br.readLine();
            if (linha == null) throw new Exception("Arquivo vazio");

            String[] partesCabecalho = linha.trim().split("\\s+");
            int totalVertices = Integer.parseInt(partesCabecalho[0]);
            
            Grafo grafo = new Grafo(totalVertices);

            // Lê as coordenadas de cada vértice
            for (int i = 0; i < totalVertices; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                int id = Integer.parseInt(partes[0]);
                double x = Double.parseDouble(partes[1].replace(",", "."));
                double y = Double.parseDouble(partes[2].replace(",", "."));
                
                grafo.adicionarVertice(id, x, y);
            }

            // Lê total de arestas
            linha = br.readLine();
            String[] partesArestas = linha.trim().split("\\s+");
            int totalArestas = Integer.parseInt(partesArestas[0]);

            // Lê as conexões (from -> to)
            for (int i = 0; i < totalArestas; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                int from = Integer.parseInt(partes[1]);
                int to = Integer.parseInt(partes[2]);
                
                int direcional = 0;
                if (partes.length >= 4) {
                    direcional = Integer.parseInt(partes[3]);
                }
                
                if (direcional == 1) {
                    grafo.adicionarArestaDirecionada(from, to);
                } else {
                    grafo.adicionarArestaBidirecional(from, to);
                }
            }
            
            return grafo;
        }
    }
}