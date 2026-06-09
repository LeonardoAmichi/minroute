package src.core;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Essa classe funciona como um detetive de mapas do OpenStreetMap (.osm).
 * Ela lê aqueles arquivos cheios de tags do OSM (que parecem HTML/XML) e extrai 
 * apenas os pontos (nós) e as ruas (vias) que precisamos para traçar nossas rotas.
 */
public class ParserOSM {

    // Essa constante representa o tamanho do planeta! Usamos o raio aproximado da Terra (em metros)
    // para transformar as coordenadas globais em um plano X e Y (tipo um mapa de papel)
    private static final double RAIO_TERRA = 6378137.0; 

    /**
     * Uma ViaOSM representa uma rua ou trecho de estrada no formato do OpenStreetMap.
     */
    static class ViaOSM {
        // A rua é composta por uma sequência de pontos ligados
        List<Long> nos = new ArrayList<>();
        // Indica o sentido do fluxo: 0 = mão dupla, 1 = vai em frente, -1 = contramão
        int oneway = 0; 
    }

    /**
     * A função principal que lê o arquivo .osm e nos devolve um Grafo pronto para o uso.
     */
    public static Grafo carregar(String caminhoArquivo) throws Exception {
        // Como o OSM usa IDs enormes e aleatórios, usamos um mapa temporário para não nos perdermos
        Map<Long, Grafo.Vertice> verticesTemp = new HashMap<>();
        List<ViaOSM> vias = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            String linha;
            ViaOSM viaAtual = null;

            // Lemos o arquivo inteiro, linha por linha
            while ((linha = br.readLine()) != null) {
                // 1. Encontramos um Ponto (Node no OSM)
                if (linha.contains("<node")) {
                    long id = extrairAtributoLong(linha, "id=");
                    double lat = extrairAtributoDouble(linha, "lat=");
                    double lon = extrairAtributoDouble(linha, "lon=");

                    // A mágica matemática! Precisamos converter Latitude e Longitude da esfera da Terra
                    // para um papel plano (Projeção Mercator Simples), gerando o X e Y do nosso mapa.
                    double x = RAIO_TERRA * Math.toRadians(lon);
                    double y = RAIO_TERRA * Math.log(Math.tan(Math.PI / 4 + Math.toRadians(lat) / 2));

                    // Guardamos o ponto na nossa lista de espera
                    verticesTemp.put(id, new Grafo.Vertice(id, x, y));
                }
                
                // 2. Encontramos o começo de uma Rua (Way no OSM)
                if (linha.contains("<way")) {
                    viaAtual = new ViaOSM(); // Começamos a montar uma nova rua
                }
                
                // Procuramos pelas tags dentro da Rua para descobrir suas regras (ex: se é mão única)
                if (linha.contains("<tag") && viaAtual != null) {
                    if (linha.contains("k=\"oneway\"")) {
                        String v = extrairString(linha, "v=");
                        if (v.equals("yes") || v.equals("true") || v.equals("1")) {
                            viaAtual.oneway = 1; // Só vai
                        } else if (v.equals("-1") || v.equals("reverse")) {
                            viaAtual.oneway = -1; // Só vem (contramão)
                        }
                    }
                }
                
                // 3. Encontramos um ponto de conexão ("nd" de node reference) dentro dessa Rua
                if (linha.contains("<nd") && viaAtual != null) {
                    long refId = extrairAtributoLong(linha, "ref=");
                    // Se for um ponto que a gente já guardou antes, adicionamos na rua
                    if (verticesTemp.containsKey(refId)) {
                        viaAtual.nos.add(refId);
                    }
                }
                
                // 4. Chegamos ao final da Rua
                if (linha.contains("</way>") && viaAtual != null) {
                    // Só nos interessa ruas que liguem pelo menos 2 pontos (não dá pra fazer rua de 1 ponto só!)
                    if (viaAtual.nos.size() > 1) {
                        vias.add(viaAtual);
                    }
                    viaAtual = null; // Terminamos de ler esta rua, prepara para a próxima
                }
            }
        }

        // 5. Agora vamos montar o nosso Grafo final organizadinho!
        Grafo grafo = new Grafo(verticesTemp.size());
        
        // Vamos dar IDs simples (0, 1, 2...) em vez dos números gigantes do OSM
        Map<Long, Integer> mapaIds = new HashMap<>();
        int novoId = 0;
        
        for (Grafo.Vertice vOriginal : verticesTemp.values()) {
            mapaIds.put(vOriginal.id, novoId); // Guarda a tradução: ID gigante -> ID novo (simples)
            grafo.adicionarVertice(novoId, vOriginal.x, vOriginal.y); // Adiciona no mapa de verdade
            novoId++;
        }

        // Por fim, vamos traduzir todas as ruas conectando com os IDs novos
        for (ViaOSM via : vias) {
            for (int i = 0; i < via.nos.size() - 1; i++) {
                long fromOriginal = via.nos.get(i);
                long toOriginal = via.nos.get(i + 1);
                
                Integer fromInterno = mapaIds.get(fromOriginal);
                Integer toInterno = mapaIds.get(toOriginal);
                
                if (fromInterno != null && toInterno != null) {
                    // Adicionamos a conexão respeitando a mão da via!
                    if (via.oneway == 1) {
                        grafo.adicionarArestaDirecionada(fromInterno, toInterno);
                    } else if (via.oneway == -1) {
                        grafo.adicionarArestaDirecionada(toInterno, fromInterno);
                    } else {
                        grafo.adicionarArestaBidirecional(fromInterno, toInterno);
                    }
                }
            }
        }

        return grafo;
    }

    // ---------------------------------------------------------------------------------
    // Funções auxiliares (Os pequenos ajudantes que pinçam textos do meio das tags XML)
    // ---------------------------------------------------------------------------------

    private static long extrairAtributoLong(String linha, String atributo) {
        try {
            return Long.parseLong(extrairString(linha, atributo));
        } catch (Exception e) {
            return -1L; // Retorna um número que indica que falhou em encontrar
        }
    }

    private static double extrairAtributoDouble(String linha, String atributo) {
        try {
            return Double.parseDouble(extrairString(linha, atributo));
        } catch (Exception e) {
            return 0.0;
        }
    }

    /**
     * Esse método é o cara que vai lá no texto da linha, procura por uma palavrinha chave
     * (por exemplo "lat="), e rouba tudo o que está escrito entre as aspas logo depois dela.
     */
    private static String extrairString(String linha, String atributo) {
        int index = linha.indexOf(atributo);
        if (index == -1) return "0";
        
        // Acha a primeira aspa depois do nome do atributo
        int aspas1 = linha.indexOf("\"", index);
        // Acha a aspa que fecha o texto
        int aspas2 = linha.indexOf("\"", aspas1 + 1);
        
        if (aspas1 != -1 && aspas2 != -1) {
            return linha.substring(aspas1 + 1, aspas2);
        }
        return "0";
    }
}