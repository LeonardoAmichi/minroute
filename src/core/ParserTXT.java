package src.core;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.Locale;
import java.util.Scanner;

/**
 * Parser para arquivos de formato TXT simples. Converte o conteúdo em um objeto `Grafo`.
 */
public class ParserTXT {

    /**
     * Carrega um grafo a partir de um arquivo TXT estruturado.
     */
    public static Grafo parse(String caminhoArquivo) {
        Grafo grafo = null;

        try (Scanner scanner = new Scanner(new File(caminhoArquivo))) {
            // Configura o Scanner para interpretar ponto como separador decimal
            scanner.useLocale(Locale.US);

            // 1. Localiza o cabeçalho com N (vértices) e M (arestas), ignorando comentários e linhas vazias
            int n = -1;
            int m = -1;
            while (scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                // Ignora linhas vazias e comentários iniciados por '#'
                if (linha.isEmpty() || linha.startsWith("#")) {
                    continue;
                }
                
                String[] partes = linha.split("\\s+");
                // Se a linha conter N e M, consideramos encontrada a informação de cabeçalho
                if (partes.length >= 2) {
                    n = Integer.parseInt(partes[0]);
                    m = Integer.parseInt(partes[1]);
                    break;
                }
            }

            // Valida presença do cabeçalho com quantidades de vértices e arestas
            if (n == -1 || m == -1) {
                throw new IllegalArgumentException("Arquivo TXT mal formatado. O cabeçalho com a quantidade de vértices e arestas está faltando.");
            }

            // Inicializa o grafo com a quantidade de vértices informada
            grafo = new Grafo(n);

            // 2. Lê os detalhes de cada vértice: id, X, Y
            int verticesLidos = 0;
            while (verticesLidos < n && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 3) {
                    int id = Integer.parseInt(partes[0]);
                    double x = Double.parseDouble(partes[1].replace(",", "."));
                    double y = Double.parseDouble(partes[2].replace(",", "."));
                    
                    // Adiciona o vértice ao grafo
                    grafo.adicionarVertice(id, x, y);
                    verticesLidos++;
                }
            }

            // 3. Lê as arestas (conexões) entre os vértices
            int arestasLidas = 0;
            while (arestasLidas < m && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 2) {
                    int origem = Integer.parseInt(partes[0]);
                    int destino = Integer.parseInt(partes[1]);
                    
                    // Se não houver campo de direção, assume-se aresta bidirecional
                    int direcao = 0;
                    if (partes.length >= 3) {
                        direcao = Integer.parseInt(partes[2]);
                    }

                    // Adiciona aresta respeitando a direção informada
                    if (direcao == 1) {
                        grafo.adicionarArestaDirecionada(origem, destino);
                    } else {
                        grafo.adicionarArestaBidirecional(origem, destino);
                    }
                    arestasLidas++;
                }
            }

        } catch (FileNotFoundException e) {
            System.err.println("Arquivo TXT não encontrado: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("Erro ao ler o arquivo TXT: " + e.getMessage());
        }

        // Retorna o grafo construído ou null em caso de falha
        return grafo;
    }
}
