package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Service: WhatsApp Business API
 * ===============================
 *
 * Integracao com WhatsApp Business API para envio de mensagens.
 */
@Service
public class WhatsAppService {

    private static final Logger logger = LoggerFactory.getLogger(WhatsAppService.class);

    @Value("${whatsapp.api.url:https://api.whatsapp.mock}")
    private String apiUrl;

    @Value("${whatsapp.api.token:mock-token}")
    private String apiToken;

    /**
     * Envia mensagem via WhatsApp.
     *
     * @param telefone Numero do telefone (formato: 5511999999999)
     * @param mensagem Texto da mensagem
     * @return Resultado do envio
     */
    public SendResult enviarMensagem(String telefone, String mensagem) {
        logger.info("Enviando WhatsApp para {} - Mensagem: {}...", telefone, mensagem.substring(0, Math.min(50, mensagem.length())));

        // MOCK: Em producao, chamar API real do WhatsApp Business
        try {
            // Simula chamada a API
            Thread.sleep(100);

            String messageId = "wamid." + System.currentTimeMillis();

            logger.info("WhatsApp enviado com sucesso - MessageID: {}", messageId);

            return new SendResult(true, messageId, null);

        } catch (Exception e) {
            logger.error("Erro ao enviar WhatsApp: {}", e.getMessage());
            return new SendResult(false, null, e.getMessage());
        }
    }

    /**
     * Envia template de mensagem.
     *
     * @param telefone Numero do telefone
     * @param templateName Nome do template
     * @param parametros Parametros do template
     * @return Resultado do envio
     */
    public SendResult enviarTemplate(String telefone, String templateName, String... parametros) {
        logger.info("Enviando template {} para {}", templateName, telefone);

        // MOCK: Em producao, chamar API real
        String messageId = "wamid.template." + System.currentTimeMillis();
        return new SendResult(true, messageId, null);
    }

    /**
     * Resultado do envio de mensagem.
     */
    public static class SendResult {
        private final boolean success;
        private final String messageId;
        private final String error;

        public SendResult(boolean success, String messageId, String error) {
            this.success = success;
            this.messageId = messageId;
            this.error = error;
        }

        public boolean isSuccess() { return success; }
        public String getMessageId() { return messageId; }
        public String getError() { return error; }
    }
}
