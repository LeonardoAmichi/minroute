package src.core;

import java.io.BufferedReader;
import java.io.FileReader;

/**
 * Parser para arquivos no formato .poly. Converte o conteúdo textual em um objeto
 * `Grafo` pronto para uso pelo motor de rota.
 */
public class ParserPoly {

    /**
     * Carrega um grafo a partir de um arquivo .poly. Lança exceção em caso de erro de leitura
     * ou formatação.
     */
    public static Grafo carregar(String caminhoArquivo) throws Exception {
        // Abre o arquivo e itera pelas linhas para construir o grafo
        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            
            // Lê o cabeçalho contendo o número total de vértices
            String linha = br.readLine();
            if (linha == null) throw new Exception("Ops! O arquivo parece estar vazio.");

            // Extrai o total de vértices e inicializa a estrutura
            String[] partesCabecalho = linha.trim().split("\\s+");
            int totalVertices = Integer.parseInt(partesCabecalho[0]);
            
            Grafo grafo = new Grafo(totalVertices);

            // Lê as coordenadas (x, y) de cada vértice
            for (int i = 0; i < totalVertices; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                
                int id = Integer.parseInt(partes[0]);
                // Normaliza separador decimal (vírgula -> ponto) e converte para double
                double x = Double.parseDouble(partes[1].replace(",", "."));
                double y = Double.parseDouble(partes[2].replace(",", "."));
                
                // Adiciona o vértice no grafo
                grafo.adicionarVertice(id, x, y);
            }

            // Lê o cabeçalho das arestas com o total informado
            linha = br.readLine();
            String[] partesArestas = linha.trim().split("\\s+");
            int totalArestas = Integer.parseInt(partesArestas[0]);

            // Lê cada definição de aresta informando origem, destino e opcionalmente direção
            for (int i = 0; i < totalArestas; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                
                int from = Integer.parseInt(partes[1]);
                int to = Integer.parseInt(partes[2]);
                
                int direcional = 0;
                // Se presente, o quarto campo indica se a aresta é direcionada (1) ou bidirecional (0)
                if (partes.length >= 4) {
                    direcional = Integer.parseInt(partes[3]);
                }
                
                // Adiciona a aresta ao grafo respeitando a direção informada
                if (direcional == 1) {
                    grafo.adicionarArestaDirecionada(from, to);
                } else {
                    grafo.adicionarArestaBidirecional(from, to);
                }
            }
            
            // Retorna o grafo construído
            return grafo;
        }
    }
}