package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * Service: Machine Learning - Estratificacao de Risco
 * =====================================================
 *
 * Integracao com modelo XGBoost para estratificacao de risco.
 * Classifica na Piramide Kaiser: BAIXO, MODERADO, ALTO, COMPLEXO.
 */
@Service
public class MLService {

    private static final Logger logger = LoggerFactory.getLogger(MLService.class);

    @Value("${ml.api.url:http://localhost:5000}")
    private String mlApiUrl;

    /**
     * Calcula risco do beneficiario usando modelo ML.
     *
     * @param screeningScore Score do screening (0-100)
     * @param idade Idade do beneficiario
     * @param temDoencaCronica Se tem doenca cronica
     * @param imc IMC calculado
     * @param fumante Se e fumante
     * @return Resultado da estratificacao
     * @throws MLServiceException Se falhar a chamada ao ML
     */
    public RiskResult calcularRisco(Integer screeningScore, Integer idade,
                                     Boolean temDoencaCronica, Double imc, Boolean fumante)
            throws MLServiceException {

        logger.info("Calculando risco - Score: {}, Idade: {}, Cronico: {}, IMC: {}, Fumante: {}",
                    screeningScore, idade, temDoencaCronica, imc, fumante);

        try {
            // MOCK: Em producao, chamar API do modelo ML
            // Simula predicao baseada em regras simplificadas

            double scoreRisco = calcularScoreRisco(screeningScore, idade, temDoencaCronica, imc, fumante);
            String nivelRisco = classificarNivel(scoreRisco);
            double probInternacao = scoreRisco * 0.3; // Estimativa simplificada

            List<String> fatores = identificarFatores(idade, temDoencaCronica, imc, fumante);

            RiskResult resultado = new RiskResult();
            resultado.setNivelRisco(nivelRisco);
            resultado.setScoreRisco(scoreRisco);
            resultado.setProbabilidadeInternacao(probInternacao);
            resultado.setFatoresRisco(String.join(", ", fatores));

            logger.info("Risco calculado - Nivel: {}, Score: {:.2f}", nivelRisco, scoreRisco);

            return resultado;

        } catch (Exception e) {
            logger.error("Erro ao calcular risco: {}", e.getMessage());
            throw new MLServiceException("Falha no calculo de risco: " + e.getMessage(), e);
        }
    }

    private double calcularScoreRisco(Integer screeningScore, Integer idade,
                                       Boolean temDoencaCronica, Double imc, Boolean fumante) {
        double score = 0.0;

        // Inverter screening (menor score = maior risco)
        score += (100 - screeningScore) * 0.003;

        // Idade
        if (idade > 70) score += 0.25;
        else if (idade > 60) score += 0.15;
        else if (idade > 50) score += 0.08;

        // Doenca cronica
        if (temDoencaCronica) score += 0.20;

        // IMC
        if (imc > 35) score += 0.15;
        else if (imc > 30) score += 0.10;
        else if (imc > 27) score += 0.05;

        // Fumante
        if (fumante) score += 0.15;

        return Math.min(1.0, Math.max(0.0, score));
    }

    private String classificarNivel(double score) {
        // Piramide Kaiser
        if (score >= 0.75) return "COMPLEXO";     // 5%
        if (score >= 0.55) return "ALTO";         // 15%
        if (score >= 0.30) return "MODERADO";     // 30%
        return "BAIXO";                            // 50%
    }

    private List<String> identificarFatores(Integer idade, Boolean temDoencaCronica,
                                             Double imc, Boolean fumante) {
        List<String> fatores = new ArrayList<>();

        if (idade > 65) fatores.add("IDADE_AVANCADA");
        if (temDoencaCronica) fatores.add("DOENCA_CRONICA");
        if (imc > 30) fatores.add("OBESIDADE");
        if (fumante) fatores.add("TABAGISMO");

        if (fatores.isEmpty()) fatores.add("NENHUM_FATOR_IDENTIFICADO");

        return fatores;
    }

    /**
     * Resultado da estratificacao de risco.
     */
    public static class RiskResult {
        private String nivelRisco;
        private double scoreRisco;
        private double probabilidadeInternacao;
        private String fatoresRisco;

        public String getNivelRisco() { return nivelRisco; }
        public void setNivelRisco(String nivelRisco) { this.nivelRisco = nivelRisco; }

        public double getScoreRisco() { return scoreRisco; }
        public void setScoreRisco(double scoreRisco) { this.scoreRisco = scoreRisco; }

        public double getProbabilidadeInternacao() { return probabilidadeInternacao; }
        public void setProbabilidadeInternacao(double probabilidadeInternacao) {
            this.probabilidadeInternacao = probabilidadeInternacao;
        }

        public String getFatoresRisco() { return fatoresRisco; }
        public void setFatoresRisco(String fatoresRisco) { this.fatoresRisco = fatoresRisco; }
    }

    /**
     * Excecao especifica do servico ML.
     */
    public static class MLServiceException extends Exception {
        public MLServiceException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
