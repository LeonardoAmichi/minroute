package src.core;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.Locale;
import java.util.Scanner;

/**
 * Essa classe atua como um tradutor para arquivos de texto simples (.txt).
 * Ela lê o arquivo, extrai as informações sobre os pontos e as ruas e monta o nosso mapa (Grafo).
 */
public class ParserTXT {

    /**
     * Pega o caminho do arquivo TXT e transforma em um Grafo prontinho para ser usado.
     */
    public static Grafo parse(String caminhoArquivo) {
        Grafo grafo = null;

        try (Scanner scanner = new Scanner(new File(caminhoArquivo))) {
            // A gente configura o Scanner para entender que números com vírgula usam ponto (estilo americano)
            scanner.useLocale(Locale.US);

            // 1. O primeiro passo é encontrar quantos pontos (N) e quantas ruas (M) o mapa tem.
            // Ignoramos qualquer linha que seja comentário (começa com #) ou esteja vazia.
            int n = -1;
            int m = -1;
            while (scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                // Ignora linhas vazias e comentários
                if (linha.isEmpty() || linha.startsWith("#")) {
                    continue;
                }
                
                String[] partes = linha.split("\\s+");
                // Achamos a linha de cabeçalho! Ela deve ter as duas informações
                if (partes.length >= 2) {
                    n = Integer.parseInt(partes[0]);
                    m = Integer.parseInt(partes[1]);
                    break;
                }
            }

            // Se não encontramos essas informações, não tem como continuar :(
            if (n == -1 || m == -1) {
                throw new IllegalArgumentException("Arquivo TXT mal formatado. O cabeçalho com a quantidade de vértices e arestas está faltando.");
            }

            // Agora sim, preparamos o mapa com o tamanho correto
            grafo = new Grafo(n);

            // 2. Hora de ler os detalhes de cada ponto (id, posição X e posição Y)
            int verticesLidos = 0;
            while (verticesLidos < n && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 3) {
                    int id = Integer.parseInt(partes[0]);
                    double x = Double.parseDouble(partes[1].replace(",", "."));
                    double y = Double.parseDouble(partes[2].replace(",", "."));
                    
                    // Adiciona o ponto no mapa
                    grafo.adicionarVertice(id, x, y);
                    verticesLidos++;
                }
            }

            // 3. E finalmente lemos as conexões (ruas) entre esses pontos
            int arestasLidas = 0;
            while (arestasLidas < m && scanner.hasNextLine()) {
                String linha = scanner.nextLine().trim();
                if (linha.isEmpty() || linha.startsWith("#")) continue;

                String[] partes = linha.split("\\s+");
                if (partes.length >= 2) {
                    int origem = Integer.parseInt(partes[0]);
                    int destino = Integer.parseInt(partes[1]);
                    
                    // Se o arquivo não disser a direção da rua, assumimos que é mão dupla (0)
                    int direcao = 0;
                    if (partes.length >= 3) {
                        direcao = Integer.parseInt(partes[2]);
                    }

                    // Verifica a regra de direção e adiciona a rua no mapa
                    if (direcao == 1) {
                        grafo.adicionarArestaDirecionada(origem, destino); // Mão única
                    } else {
                        grafo.adicionarArestaBidirecional(origem, destino); // Mão dupla
                    }
                    arestasLidas++;
                }
            }

        } catch (FileNotFoundException e) {
            System.err.println("Ops! Não consegui encontrar o arquivo TXT: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("Puxa, deu um erro inesperado ao tentar ler o arquivo TXT: " + e.getMessage());
        }

        // Devolve o mapa montado ou null se algo deu errado
        return grafo;
    }
}
