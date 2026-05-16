package src.core;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ParserOSM {

    // Constantes para a conversão de coordenadas (raio da Terra aproximado)
    private static final double RAIO_TERRA = 6378137.0; 

    public static Grafo carregar(String caminhoArquivo) throws Exception {
        Map<Long, Grafo.Vertice> verticesTemp = new HashMap<>();
        List<List<Long>> vias = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            String linha;
            List<Long> viaAtual = null;

            while ((linha = br.readLine()) != null) {
                // 1. Processa os Nós (Vértices)
                if (linha.contains("<node")) {
                    long id = extrairAtributoLong(linha, "id=");
                    double lat = extrairAtributoDouble(linha, "lat=");
                    double lon = extrairAtributoDouble(linha, "lon=");

                    // Precisamos converter Latitude e Longitude para X e Y (Projeção Mercator Simples)
                    double x = RAIO_TERRA * Math.toRadians(lon);
                    double y = RAIO_TERRA * Math.log(Math.tan(Math.PI / 4 + Math.toRadians(lat) / 2));

                    // No OSM, os IDs podem ser muito grandes. Usaremos um HashMap temporário.
                    verticesTemp.put(id, new Grafo.Vertice(id, x, y));
                }
                
                // 2. Processa o início de uma Via (Arestas)
                else if (linha.contains("<way")) {
                    viaAtual = new ArrayList<>();
                }
                
                // 3. Processa os pontos de conexão dentro da Via
                else if (linha.contains("<nd") && viaAtual != null) {
                    long refId = extrairAtributoLong(linha, "ref=");
                    if (verticesTemp.containsKey(refId)) {
                        viaAtual.add(refId);
                    }
                }
                
                // 4. Finaliza a Via
                else if (linha.contains("</way>") && viaAtual != null) {
                    if (viaAtual.size() > 1) {
                        vias.add(viaAtual);
                    }
                    viaAtual = null;
                }
            }
        }

        // 5. Monta o Grafo final
        // Descobrimos o "maior ID" para inicializar o array do Grafo.
        // Como IDs do OSM são gigantes, vamos "achatar" os IDs para índices de 0 a N
        // para economizar memória (RNF05).
        Grafo grafo = new Grafo(verticesTemp.size());
        
        Map<Long, Integer> mapaIds = new HashMap<>();
        int novoId = 0;
        
        for (Grafo.Vertice vOriginal : verticesTemp.values()) {
            mapaIds.put(vOriginal.id, novoId);
            grafo.adicionarVertice(novoId, vOriginal.x, vOriginal.y);
            novoId++;
        }

        // Adiciona as arestas convertendo os IDs originais para os novos índices
        for (List<Long> via : vias) {
            for (int i = 0; i < via.size() - 1; i++) {
                long fromOriginal = via.get(i);
                long toOriginal = via.get(i + 1);
                
                int fromInterno = mapaIds.get(fromOriginal);
                int toInterno = mapaIds.get(toOriginal);
                
                grafo.adicionarArestaBidirecional(fromInterno, toInterno);
            }
        }

        return grafo;
    }

    // Funções auxiliares para extrair os dados entre aspas do XML
    private static long extrairAtributoLong(String linha, String atributo) {
        try {
            return Long.parseLong(extrairString(linha, atributo));
        } catch (Exception e) {
            return -1L;
        }
    }

    private static double extrairAtributoDouble(String linha, String atributo) {
        try {
            return Double.parseDouble(extrairString(linha, atributo));
        } catch (Exception e) {
            return 0.0;
        }
    }

    private static String extrairString(String linha, String atributo) {
        int index = linha.indexOf(atributo);
        if (index == -1) return "0";
        
        int aspas1 = linha.indexOf("\"", index);
        int aspas2 = linha.indexOf("\"", aspas1 + 1);
        
        if (aspas1 != -1 && aspas2 != -1) {
            return linha.substring(aspas1 + 1, aspas2);
        }
        return "0";
    }
}