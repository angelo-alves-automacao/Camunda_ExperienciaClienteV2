package com.operadora.delegates.comunicacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.WhatsAppService;

/**
 * Delegate: Comunicar Tempo Real
 * ===============================
 *
 * Responsabilidade TECNICA:
 * - Envia atualizacoes em tempo real para pacientes de alto risco
 * - Status de autorizacoes, agendamentos, resultados
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_nome (String): Nome do beneficiario
 * - beneficiario_telefone (String): Telefone
 * - navegador_nome (String): Nome do navegador responsavel
 * - jornada_status (String): Status atual da jornada
 *
 * OUTPUT (variaveis criadas):
 * - notificacao_enviada (Boolean): Se notificacao foi enviada
 * - notificacao_tipo (String): Tipo de notificacao
 */
@Component("comunicarTempoRealDelegate")
public class ComunicarTempoRealDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ComunicarTempoRealDelegate.class);

    @Autowired
    private WhatsAppService whatsAppService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando comunicacao tempo real - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String nome = getRequiredVariable(execution, "beneficiario_nome", String.class);
            String telefone = getRequiredVariable(execution, "beneficiario_telefone", String.class);
            String navegadorNome = getOptionalVariable(execution, "navegador_nome", String.class, "Equipe de Cuidados");
            String jornadaStatus = getOptionalVariable(execution, "jornada_status", String.class, "EM_ACOMPANHAMENTO");

            // 2. EXECUTAR logica tecnica
            String mensagem = String.format(
                "Ola %s! Seu navegador de saude %s esta acompanhando sua jornada. " +
                "Status atual: %s. Em caso de duvidas, responda esta mensagem.",
                nome, navegadorNome, traduzirStatus(jornadaStatus)
            );

            WhatsAppService.SendResult resultado = whatsAppService.enviarMensagem(telefone, mensagem);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("notificacao_enviada", resultado.isSuccess());
            execution.setVariable("notificacao_tipo", "ATUALIZACAO_JORNADA");
            execution.setVariable("notificacao_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Notificacao enviada - Sucesso: {}", activityId, resultado.isSuccess());

        } catch (Exception e) {
            logger.error("[{}] Erro na notificacao: {}", activityId, e.getMessage(), e);
            execution.setVariable("notificacao_enviada", false);
            execution.setVariable("delegate_status", "ERRO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw e;
        }
    }

    private String traduzirStatus(String status) {
        switch (status) {
            case "EM_ACOMPANHAMENTO": return "Em acompanhamento";
            case "AGUARDANDO_AUTORIZACAO": return "Aguardando autorizacao";
            case "AUTORIZADO": return "Autorizado";
            case "AGENDADO": return "Consulta agendada";
            case "CONCLUIDO": return "Atendimento concluido";
            default: return status;
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
