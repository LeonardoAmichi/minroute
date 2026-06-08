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

    static class ViaOSM {
        List<Long> nos = new ArrayList<>();
        int oneway = 0; // 0 = bidirectional, 1 = forward, -1 = backward
    }

    public static Grafo carregar(String caminhoArquivo) throws Exception {
        Map<Long, Grafo.Vertice> verticesTemp = new HashMap<>();
        List<ViaOSM> vias = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            String linha;
            ViaOSM viaAtual = null;

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
                if (linha.contains("<way")) {
                    viaAtual = new ViaOSM();
                }
                
                // Processa tags dentro da Via
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
                
                // 3. Processa os pontos de conexão dentro da Via
                if (linha.contains("<nd") && viaAtual != null) {
                    long refId = extrairAtributoLong(linha, "ref=");
                    if (verticesTemp.containsKey(refId)) {
                        viaAtual.nos.add(refId);
                    }
                }
                
                // 4. Finaliza a Via
                if (linha.contains("</way>") && viaAtual != null) {
                    if (viaAtual.nos.size() > 1) {
                        vias.add(viaAtual);
                    }
                    viaAtual = null;
                }
            }
        }

        // 5. Monta o Grafo final
        Grafo grafo = new Grafo(verticesTemp.size());
        
        Map<Long, Integer> mapaIds = new HashMap<>();
        int novoId = 0;
        
        for (Grafo.Vertice vOriginal : verticesTemp.values()) {
            mapaIds.put(vOriginal.id, novoId);
            grafo.adicionarVertice(novoId, vOriginal.x, vOriginal.y);
            novoId++;
        }

        // Adiciona as arestas convertendo os IDs originais para os novos índices
        for (ViaOSM via : vias) {
            for (int i = 0; i < via.nos.size() - 1; i++) {
                long fromOriginal = via.nos.get(i);
                long toOriginal = via.nos.get(i + 1);
                
                Integer fromInterno = mapaIds.get(fromOriginal);
                Integer toInterno = mapaIds.get(toOriginal);
                
                if (fromInterno != null && toInterno != null) {
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