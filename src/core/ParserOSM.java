package src.core;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Parser simples para arquivos OpenStreetMap (.osm).
 * Extrai nós e vias relevantes e converte em um objeto `Grafo`.
 */
public class ParserOSM {

    // Raio aproximado da Terra (em metros) usado na projeção para coordenadas planas
    private static final double RAIO_TERRA = 6378137.0; 

    /**
     * Representa uma via do OSM, com sequência de nós e informação de sentido (oneway).
     */
    static class ViaOSM {
        // Sequência de IDs de nós que compõem a via
        List<Long> nos = new ArrayList<>();
        // 0 = bidirecional, 1 = oneway forward, -1 = oneway reverse
        int oneway = 0; 
    }

    /**
     * Carrega um grafo a partir de um arquivo OSM, extraindo nós e ways relevantes.
     */
    public static Grafo carregar(String caminhoArquivo) throws Exception {
        // Temporários para armazenar nós e vias antes de traduzir para índices inteiros
        Map<Long, Grafo.Vertice> verticesTemp = new HashMap<>();
        List<ViaOSM> vias = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            String linha;
            ViaOSM viaAtual = null;

            // Itera sobre as linhas do arquivo OSM
            while ((linha = br.readLine()) != null) {
                // 1) Detecta definição de nó (<node>) e extrai id/lat/lon
                if (linha.contains("<node")) {
                    long id = extrairAtributoLong(linha, "id=");
                    double lat = extrairAtributoDouble(linha, "lat=");
                    double lon = extrairAtributoDouble(linha, "lon=");

                    // Converte coordenadas geográficas para projeção plana (Mercator simplificado)
                    double x = RAIO_TERRA * Math.toRadians(lon);
                    double y = RAIO_TERRA * Math.log(Math.tan(Math.PI / 4 + Math.toRadians(lat) / 2));

                    // Armazena temporariamente o vértice para posterior indexação
                    verticesTemp.put(id, new Grafo.Vertice(id, x, y));
                }
                
                // 2) Detecta início de uma via (<way>) e inicia objeto auxiliar
                if (linha.contains("<way")) {
                    viaAtual = new ViaOSM(); // Começamos a montar uma nova rua
                }
                
                // Procura tags dentro do way para obter propriedades (ex.: oneway)
                if (linha.contains("<tag") && viaAtual != null) {
                    if (linha.contains("k=\"oneway\"")) {
                        String v = extrairString(linha, "v=");
                        if (v.equals("yes") || v.equals("true") || v.equals("1")) {
                            viaAtual.oneway = 1;
                        } else if (v.equals("-1") || v.equals("reverse")) {
                            viaAtual.oneway = -1;
                        }
                    }
                }
                
                // 3) Captura referências a nós (<nd ref="...">) dentro do way
                if (linha.contains("<nd") && viaAtual != null) {
                    long refId = extrairAtributoLong(linha, "ref=");
                    // Se o nó já foi registrado, adiciona à sequência da via
                    if (verticesTemp.containsKey(refId)) {
                        viaAtual.nos.add(refId);
                    }
                }
                
                // 4) Ao fechar o way, valida e armazena a via
                if (linha.contains("</way>") && viaAtual != null) {
                    // Considera apenas vias com pelo menos dois nós
                    if (viaAtual.nos.size() > 1) {
                        vias.add(viaAtual);
                    }
                    viaAtual = null; // Terminamos de ler esta rua, prepara para a próxima
                }
            }
        }

        // 5) Constrói o grafo final traduzindo IDs OSM para índices inteiros sequenciais
        Grafo grafo = new Grafo(verticesTemp.size());
        
        // Vamos dar IDs simples (0, 1, 2...) em vez dos números gigantes do OSM
        Map<Long, Integer> mapaIds = new HashMap<>();
        int novoId = 0;
        
        for (Grafo.Vertice vOriginal : verticesTemp.values()) {
            mapaIds.put(vOriginal.id, novoId); // Guarda a tradução: ID gigante -> ID novo (simples)
            grafo.adicionarVertice(novoId, vOriginal.x, vOriginal.y); // Adiciona no mapa de verdade
            novoId++;
        }

        // Traduz e adiciona as arestas ao grafo respeitando a direção das vias
        for (ViaOSM via : vias) {
            for (int i = 0; i < via.nos.size() - 1; i++) {
                long fromOriginal = via.nos.get(i);
                long toOriginal = via.nos.get(i + 1);
                
                Integer fromInterno = mapaIds.get(fromOriginal);
                Integer toInterno = mapaIds.get(toOriginal);
                
                if (fromInterno != null && toInterno != null) {
                    // Adiciona conexão conforme atributo 'oneway'
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
    // Funções auxiliares para extrair atributos de texto nas linhas XML
    // ---------------------------------------------------------------------------------

    private static long extrairAtributoLong(String linha, String atributo) {
        try {
            return Long.parseLong(extrairString(linha, atributo));
        } catch (Exception e) {
            return -1L; // Indica falha na extração
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
     * Extrai o valor de um atributo entre aspas a partir de uma linha XML.
     * Ex.: extrairString("... lat=\"12.3\" ...", "lat=") -> "12.3"
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