package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Service: Screening de Saude
 * ============================
 *
 * Processa questionario de saude e calcula score inicial.
 */
@Service
public class ScreeningService {

    private static final Logger logger = LoggerFactory.getLogger(ScreeningService.class);

    /**
     * Realiza screening de saude do beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @return Resultado do screening
     */
    public ScreeningResult realizarScreening(String cpf) {
        logger.info("Realizando screening para CPF: {}", cpf);

        // MOCK: Em producao, buscar respostas do formulario
        // e calcular score baseado em algoritmo clinico

        ScreeningResult resultado = new ScreeningResult();

        // Simula dados de um beneficiario
        resultado.setIdade(45);
        resultado.setImc(26.5);
        resultado.setFumante(false);
        resultado.setPraticaExercicio(true);
        resultado.setTemDoencaCronica(false);

        // Calcula score (0-100, maior = mais saudavel)
        int score = calcularScore(resultado);
        resultado.setScore(score);

        // Gera JSON de respostas
        resultado.setRespostasJson(String.format(
            "{\"idade\":%d,\"imc\":%.1f,\"fumante\":%b,\"exercicio\":%b,\"cronico\":%b,\"score\":%d}",
            resultado.getIdade(), resultado.getImc(), resultado.isFumante(),
            resultado.isPraticaExercicio(), resultado.isTemDoencaCronica(), score
        ));

        logger.info("Screening concluido - Score: {}", score);

        return resultado;
    }

    private int calcularScore(ScreeningResult dados) {
        int score = 100;

        // Idade
        if (dados.getIdade() > 60) score -= 15;
        else if (dados.getIdade() > 45) score -= 5;

        // IMC
        if (dados.getImc() > 30) score -= 20;
        else if (dados.getImc() > 25) score -= 10;
        else if (dados.getImc() < 18.5) score -= 10;

        // Fatores de risco
        if (dados.isFumante()) score -= 25;
        if (!dados.isPraticaExercicio()) score -= 10;
        if (dados.isTemDoencaCronica()) score -= 20;

        return Math.max(0, Math.min(100, score));
    }

    /**
     * Resultado do screening.
     */
    public static class ScreeningResult {
        private int score;
        private int idade;
        private double imc;
        private boolean fumante;
        private boolean praticaExercicio;
        private boolean temDoencaCronica;
        private String respostasJson;

        // Getters e Setters
        public int getScore() { return score; }
        public void setScore(int score) { this.score = score; }

        public int getIdade() { return idade; }
        public void setIdade(int idade) { this.idade = idade; }

        public double getImc() { return imc; }
        public void setImc(double imc) { this.imc = imc; }

        public boolean isFumante() { return fumante; }
        public void setFumante(boolean fumante) { this.fumante = fumante; }

        public boolean isPraticaExercicio() { return praticaExercicio; }
        public void setPraticaExercicio(boolean praticaExercicio) { this.praticaExercicio = praticaExercicio; }

        public boolean isTemDoencaCronica() { return temDoencaCronica; }
        public void setTemDoencaCronica(boolean temDoencaCronica) { this.temDoencaCronica = temDoencaCronica; }

        public String getRespostasJson() { return respostasJson; }
        public void setRespostasJson(String respostasJson) { this.respostasJson = respostasJson; }
    }
}
