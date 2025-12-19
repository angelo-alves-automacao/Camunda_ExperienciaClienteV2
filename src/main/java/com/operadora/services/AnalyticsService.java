package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;

/**
 * Service: Analytics de Desfechos
 * ================================
 *
 * Analisa desfechos clinicos e operacionais.
 */
@Service
public class AnalyticsService {

    private static final Logger logger = LoggerFactory.getLogger(AnalyticsService.class);

    /**
     * Analisa desfechos do beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param nivelRisco Nivel de risco
     * @param npsScore Score NPS
     * @param jornadaId ID da jornada
     * @param processId ID do processo
     * @return Resultado da analise
     */
    public DesfechoResult analisarDesfechos(String cpf, String nivelRisco, Integer npsScore,
                                             String jornadaId, String processId) {
        logger.info("Analisando desfechos para CPF: {}, Risco: {}, NPS: {}", cpf, nivelRisco, npsScore);

        DesfechoResult resultado = new DesfechoResult();

        // Classifica desfecho baseado em NPS e nivel de risco
        String categoria = classificarDesfecho(npsScore, nivelRisco);
        resultado.setCategoria(categoria);

        // Gera metricas
        String metricas = String.format(
            "{\"cpf\":\"%s\",\"nivel_risco\":\"%s\",\"nps\":%d,\"categoria\":\"%s\",\"jornada\":\"%s\",\"processo\":\"%s\"}",
            cpf, nivelRisco, npsScore, categoria, jornadaId != null ? jornadaId : "N/A", processId
        );
        resultado.setMetricasJson(metricas);

        // Gera recomendacoes
        List<String> recomendacoes = gerarRecomendacoes(categoria, nivelRisco);
        resultado.setRecomendacoes(recomendacoes);

        logger.info("Desfecho analisado - Categoria: {}", categoria);

        return resultado;
    }

    private String classificarDesfecho(Integer npsScore, String nivelRisco) {
        if (npsScore >= 9) {
            return "POSITIVO";
        } else if (npsScore >= 7) {
            return "NEUTRO";
        } else {
            return "NEGATIVO";
        }
    }

    private List<String> gerarRecomendacoes(String categoria, String nivelRisco) {
        switch (categoria) {
            case "POSITIVO":
                return Arrays.asList(
                    "Manter frequencia de contato atual",
                    "Considerar para case de sucesso",
                    "Solicitar depoimento"
                );

            case "NEUTRO":
                return Arrays.asList(
                    "Investigar pontos de melhoria",
                    "Aumentar frequencia de contato",
                    "Oferecer beneficios adicionais"
                );

            case "NEGATIVO":
                return Arrays.asList(
                    "Contato urgente do navegador",
                    "Analise de causa raiz",
                    "Plano de recuperacao",
                    "Escalonamento para gestao"
                );

            default:
                return Arrays.asList("Avaliar manualmente");
        }
    }

    /**
     * Resultado da analise de desfechos.
     */
    public static class DesfechoResult {
        private String categoria;
        private String metricasJson;
        private List<String> recomendacoes;

        public String getCategoria() { return categoria; }
        public void setCategoria(String categoria) { this.categoria = categoria; }

        public String getMetricasJson() { return metricasJson; }
        public void setMetricasJson(String metricasJson) { this.metricasJson = metricasJson; }

        public List<String> getRecomendacoes() { return recomendacoes; }
        public void setRecomendacoes(List<String> recomendacoes) { this.recomendacoes = recomendacoes; }
    }
}
