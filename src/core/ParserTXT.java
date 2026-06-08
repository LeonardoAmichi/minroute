package src.core;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.Locale;
import java.util.Scanner;

public class ParserTXT {

    public static Grafo parse(String caminhoArquivo) {
        Grafo grafo = null;

        try (Scanner scanner = new Scanner(new File(caminhoArquivo))) {
            // Configurar locale para ler double com ponto ou vírgula
            scanner.useLocale(Locale.US);

            // 1. Encontrar a linha com N (vértices) e M (arestas) ignorando comentários
            int n = -1;
            int m = -1;
            while (scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) {
                    continue;
                }
                String[] partes = linha.split("\\s+");
                if (partes.length >= 2) {
                    n = Integer.parseInt(partes[0]);
                    m = Integer.parseInt(partes[1]);
                    break;
                }
            }

            if (n == -1 || m == -1) {
                throw new IllegalArgumentException("Arquivo TXT mal formatado. Cabeçalho ausente.");
            }

            grafo = new Grafo(n);

            // 2. Ler N vértices (id x y)
            int verticesLidos = 0;
            while (verticesLidos < n && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 3) {
                    int id = Integer.parseInt(partes[0]);
                    double x = Double.parseDouble(partes[1]);
                    double y = Double.parseDouble(partes[2]);
                    grafo.adicionarVertice(id, x, y);
                    verticesLidos++;
                }
            }

            // 3. Ler M arestas (origem destino direcao)
            int arestasLidas = 0;
            while (arestasLidas < m && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 2) {
                    int origem = Integer.parseInt(partes[0]);
                    int destino = Integer.parseInt(partes[1]);
                    
                    // Se não tiver a 3a coluna (direcao), assume mão dupla (0)
                    int direcao = 0;
                    if (partes.length >= 3) {
                        direcao = Integer.parseInt(partes[2]);
                    }

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
            System.err.println("Erro ao fazer parse do arquivo TXT: " + e.getMessage());
        }

        return grafo;
    }
}
