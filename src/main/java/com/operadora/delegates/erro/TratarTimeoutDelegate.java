package com.operadora.delegates.erro;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.NotificacaoService;

/**
 * Delegate: Tratar Timeout Screening
 * ====================================
 *
 * Responsabilidade TECNICA:
 * - Trata timeout quando beneficiario nao responde screening
 * - Envia lembrete ou notifica equipe
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - beneficiario_nome (String): Nome
 * - beneficiario_telefone (String): Telefone
 *
 * OUTPUT (variaveis criadas):
 * - timeout_tratado (Boolean): Se timeout foi tratado
 * - timeout_acao (String): Acao tomada
 * - timeout_motivo (String): Motivo do timeout
 */
@Component("tratarTimeoutDelegate")
public class TratarTimeoutDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(TratarTimeoutDelegate.class);

    @Autowired
    private NotificacaoService notificacaoService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.warn("[{}] Tratando timeout de screening - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getOptionalVariable(execution, "beneficiario_cpf", String.class, "");
            String nome = getOptionalVariable(execution, "beneficiario_nome", String.class, "Beneficiario");
            String telefone = getOptionalVariable(execution, "beneficiario_telefone", String.class, "");

            // 2. EXECUTAR logica tecnica
            // Registra o timeout
            logger.info("[{}] Beneficiario {} nao completou screening em 24h", activityId, nome);

            // Envia lembrete se tiver telefone
            if (telefone != null && !telefone.isEmpty()) {
                notificacaoService.enviarLembrete(telefone, nome,
                    "Voce ainda nao completou seu questionario de saude. Complete para receber um atendimento personalizado!");
            }

            // Notifica equipe de operacoes
            notificacaoService.notificarEquipe("TIMEOUT_SCREENING",
                String.format("Beneficiario %s (CPF: %s) nao completou screening em 24h", nome, cpf));

            // 3. ESCREVER variaveis de saida
            execution.setVariable("timeout_tratado", true);
            execution.setVariable("timeout_acao", "LEMBRETE_ENVIADO");
            execution.setVariable("timeout_motivo", "SCREENING_NAO_COMPLETADO_24H");
            execution.setVariable("timeout_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Timeout tratado - Acao: LEMBRETE_ENVIADO", activityId);

        } catch (Exception e) {
            logger.error("[{}] Erro ao tratar timeout: {}", activityId, e.getMessage(), e);
            execution.setVariable("timeout_tratado", false);
            execution.setVariable("delegate_status", "ERRO");
            execution.setVariable("delegate_erro", e.getMessage());
            // Nao relanca excecao - timeout ja e um fluxo de erro
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T getOptionalVariable(DelegateExecution execution, String name, Class<T> type, T defaultValue) {
        Object value = execution.getVariable(name);
        return value != null ? (T) value : defaultValue;
    }
}
