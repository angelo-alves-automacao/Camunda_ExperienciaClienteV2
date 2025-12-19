package com.operadora.delegates.comunicacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.WhatsAppService;

/**
 * Delegate: Comunicacao Proativa
 * ===============================
 *
 * Responsabilidade TECNICA:
 * - Envia comunicacoes proativas via WhatsApp
 * - Lembretes, dicas de saude, campanhas preventivas
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_nome (String): Nome do beneficiario
 * - beneficiario_telefone (String): Telefone
 * - proxima_acao (String): Tipo de acao a comunicar
 * - acoes_preventivas (String[]): Lista de acoes
 *
 * OUTPUT (variaveis criadas):
 * - comunicacao_enviada (Boolean): Se mensagem foi enviada
 * - comunicacao_tipo (String): Tipo de comunicacao enviada
 */
@Component("comunicacaoProativaDelegate")
public class ComunicacaoProativaDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ComunicacaoProativaDelegate.class);

    @Autowired
    private WhatsAppService whatsAppService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando comunicacao proativa - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String nome = getRequiredVariable(execution, "beneficiario_nome", String.class);
            String telefone = getRequiredVariable(execution, "beneficiario_telefone", String.class);
            String proximaAcao = getOptionalVariable(execution, "proxima_acao", String.class, "LEMBRETE_SAUDE");

            // 2. EXECUTAR logica tecnica
            String mensagem = construirMensagem(nome, proximaAcao);
            WhatsAppService.SendResult resultado = whatsAppService.enviarMensagem(telefone, mensagem);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("comunicacao_enviada", resultado.isSuccess());
            execution.setVariable("comunicacao_tipo", proximaAcao);
            execution.setVariable("comunicacao_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Comunicacao enviada - Tipo: {}, Sucesso: {}",
                        activityId, proximaAcao, resultado.isSuccess());

        } catch (Exception e) {
            logger.error("[{}] Erro na comunicacao: {}", activityId, e.getMessage(), e);
            execution.setVariable("comunicacao_enviada", false);
            execution.setVariable("delegate_status", "ERRO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw e;
        }
    }

    private String construirMensagem(String nome, String tipoAcao) {
        switch (tipoAcao) {
            case "VACINA":
                return String.format("Ola %s! Chegou a hora de atualizar suas vacinas. " +
                    "Consulte a rede credenciada mais proxima.", nome);
            case "CHECKUP":
                return String.format("Ola %s! Voce esta em dia com seus exames de rotina? " +
                    "Agende seu checkup anual.", nome);
            case "MEDICAMENTO":
                return String.format("Ola %s! Lembre-se de tomar seus medicamentos conforme prescrito.", nome);
            default:
                return String.format("Ola %s! A Operadora Digital do Futuro esta cuidando de voce. " +
                    "Qualquer duvida, estamos aqui!", nome);
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T getRequiredVariable(DelegateExecution execution, String name, Class<T> type) {
        Object value = execution.getVariable(name);
        if (value == null) {
            throw new IllegalArgumentException("Variavel obrigatoria nao encontrada: " + name);
        }
        return (T) value;
    }

    @SuppressWarnings("unchecked")
    private <T> T getOptionalVariable(DelegateExecution execution, String name, Class<T> type, T defaultValue) {
        Object value = execution.getVariable(name);
        return value != null ? (T) value : defaultValue;
    }
}
