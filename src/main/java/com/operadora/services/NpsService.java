package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * Service: NPS - Net Promoter Score
 * ===================================
 *
 * Coleta e analisa NPS dos beneficiarios.
 */
@Service
public class NpsService {

    private static final Logger logger = LoggerFactory.getLogger(NpsService.class);

    @Autowired
    private WhatsAppService whatsAppService;

    /**
     * Coleta NPS do beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param nome Nome do beneficiario
     * @param telefone Telefone
     * @return Resultado do NPS
     */
    public NpsResult coletarNps(String cpf, String nome, String telefone) {
        logger.info("Coletando NPS para: {} ({})", nome, cpf);

        // Envia pesquisa NPS
        String mensagem = String.format(
            "Ola %s! De 0 a 10, o quanto voce recomendaria a Operadora Digital do Futuro " +
            "para um amigo ou familiar?",
            nome
        );

        whatsAppService.enviarMensagem(telefone, mensagem);

        // MOCK: Em producao, aguardar resposta real
        NpsResult resultado = new NpsResult();
        resultado.setScore(8); // Simula resposta
        resultado.setComentario("Atendimento muito bom, rapido e eficiente.");
        resultado.setCategoria(classificarNps(resultado.getScore()));

        logger.info("NPS coletado - Score: {}, Categoria: {}", resultado.getScore(), resultado.getCategoria());

        return resultado;
    }

    private String classificarNps(int score) {
        if (score >= 9) return "PROMOTOR";
        if (score >= 7) return "NEUTRO";
        return "DETRATOR";
    }

    /**
     * Resultado do NPS.
     */
    public static class NpsResult {
        private int score;
        private String categoria;
        private String comentario;

        public int getScore() { return score; }
        public void setScore(int score) { this.score = score; }

        public String getCategoria() { return categoria; }
        public void setCategoria(String categoria) { this.categoria = categoria; }

        public String getComentario() { return comentario; }
        public void setComentario(String comentario) { this.comentario = comentario; }
    }
}
