package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * Service: Notificacoes Internas
 * ===============================
 *
 * Gerencia notificacoes para equipe interna e beneficiarios.
 */
@Service
public class NotificacaoService {

    private static final Logger logger = LoggerFactory.getLogger(NotificacaoService.class);

    @Autowired
    private WhatsAppService whatsAppService;

    /**
     * Envia lembrete ao beneficiario.
     *
     * @param telefone Telefone do beneficiario
     * @param nome Nome do beneficiario
     * @param mensagem Mensagem de lembrete
     */
    public void enviarLembrete(String telefone, String nome, String mensagem) {
        logger.info("Enviando lembrete para {} - {}", nome, telefone);

        String mensagemCompleta = String.format("Ola %s! %s", nome, mensagem);
        whatsAppService.enviarMensagem(telefone, mensagemCompleta);
    }

    /**
     * Notifica equipe interna.
     *
     * @param tipo Tipo de notificacao (TIMEOUT_SCREENING, ERRO_INTEGRACAO, etc)
     * @param detalhes Detalhes da notificacao
     */
    public void notificarEquipe(String tipo, String detalhes) {
        logger.warn("NOTIFICACAO EQUIPE [{}]: {}", tipo, detalhes);

        // MOCK: Em producao, enviar para Slack, Teams, email, etc.
        // Exemplo de integracao:
        // slackService.enviarMensagem("#alertas-operadora", tipo + ": " + detalhes);
        // emailService.enviar("operacoes@operadora.com", tipo, detalhes);

        // Por enquanto, apenas loga
        logger.info("Notificacao registrada para equipe de operacoes");
    }

    /**
     * Envia alerta critico.
     *
     * @param tipo Tipo do alerta
     * @param mensagem Mensagem do alerta
     */
    public void enviarAlertaCritico(String tipo, String mensagem) {
        logger.error("ALERTA CRITICO [{}]: {}", tipo, mensagem);

        // MOCK: Em producao, enviar SMS para plantao, ligar automaticamente, etc.
        notificarEquipe("CRITICO_" + tipo, mensagem);
    }
}
