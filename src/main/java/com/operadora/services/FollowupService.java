package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * Service: Follow-up
 * ===================
 *
 * Gerencia follow-up pos-atendimento.
 */
@Service
public class FollowupService {

    private static final Logger logger = LoggerFactory.getLogger(FollowupService.class);

    @Autowired
    private WhatsAppService whatsAppService;

    /**
     * Realiza follow-up com o beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param nome Nome do beneficiario
     * @param telefone Telefone
     * @param jornadaId ID da jornada (opcional)
     * @return Resultado do follow-up
     */
    public FollowupResult realizarFollowup(String cpf, String nome, String telefone, String jornadaId) {
        logger.info("Realizando follow-up para: {} ({})", nome, cpf);

        // Envia mensagem de follow-up
        String mensagem = String.format(
            "Ola %s! Como voce esta se sentindo apos seu atendimento? " +
            "Responda de 1 a 5, sendo 5 muito satisfeito.",
            nome
        );

        whatsAppService.enviarMensagem(telefone, mensagem);

        // MOCK: Em producao, aguardar resposta ou usar formulario
        FollowupResult resultado = new FollowupResult();
        resultado.setResposta("Estou me sentindo bem, obrigado!");
        resultado.setSatisfacao(4); // Simula resposta

        logger.info("Follow-up realizado - Satisfacao: {}/5", resultado.getSatisfacao());

        return resultado;
    }

    /**
     * Resultado do follow-up.
     */
    public static class FollowupResult {
        private String resposta;
        private int satisfacao;

        public String getResposta() { return resposta; }
        public void setResposta(String resposta) { this.resposta = resposta; }

        public int getSatisfacao() { return satisfacao; }
        public void setSatisfacao(int satisfacao) { this.satisfacao = satisfacao; }
    }
}
