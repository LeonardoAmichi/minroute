package src.core;

import java.io.BufferedReader;
import java.io.FileReader;

/**
 * Essa classe funciona como um "leitor/tradutor" de arquivos do tipo .poly.
 * Ela pega o arquivo de texto e transforma tudo na estrutura do nosso Grafo (mapa).
 */
public class ParserPoly {

    /**
     * Tenta abrir o arquivo, ler linha por linha e montar o mapa a partir dele.
     * Retorna o Grafo completinho e pronto para uso!
     */
    public static Grafo carregar(String caminhoArquivo) throws Exception {
        // Tenta abrir o arquivo para leitura
        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            
            // Lê a primeira linha, que costuma ter o total de vértices (pontos) do mapa
            String linha = br.readLine();
            if (linha == null) throw new Exception("Ops! O arquivo parece estar vazio.");

            // Pega o número e cria um novo Grafo preparado para esse tamanho
            String[] partesCabecalho = linha.trim().split("\\s+");
            int totalVertices = Integer.parseInt(partesCabecalho[0]);
            
            Grafo grafo = new Grafo(totalVertices);

            // Agora, vamos ler as coordenadas (x, y) de cada vértice
            for (int i = 0; i < totalVertices; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                
                int id = Integer.parseInt(partes[0]);
                // Transformamos vírgulas em pontos para o Java entender as casas decimais direitinho
                double x = Double.parseDouble(partes[1].replace(",", "."));
                double y = Double.parseDouble(partes[2].replace(",", "."));
                
                // Adicionamos esse ponto ao nosso mapa
                grafo.adicionarVertice(id, x, y);
            }

            // Depois dos pontos, o arquivo nos diz o total de arestas (caminhos/ruas)
            linha = br.readLine();
            String[] partesArestas = linha.trim().split("\\s+");
            int totalArestas = Integer.parseInt(partesArestas[0]);

            // Por fim, lemos as conexões dizendo de qual ponto sai e para qual vai (from -> to)
            for (int i = 0; i < totalArestas; i++) {
                linha = br.readLine();
                String[] partes = linha.trim().split("\\s+");
                
                int from = Integer.parseInt(partes[1]);
                int to = Integer.parseInt(partes[2]);
                
                int direcional = 0;
                // Em alguns casos, a linha avisa se a rua é de mão única (1) ou dupla (0)
                if (partes.length >= 4) {
                    direcional = Integer.parseInt(partes[3]);
                }
                
                // Adiciona o caminho no mapa com a regra de direção correta
                if (direcional == 1) {
                    grafo.adicionarArestaDirecionada(from, to);
                } else {
                    grafo.adicionarArestaBidirecional(from, to);
                }
            }
            
            // Retorna o mapa prontinho para o uso
            return grafo;
        }
    }
}