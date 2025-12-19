package com.operadora.delegates.erro;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.NotificacaoService;

/**
 * Delegate: Tratar Erro Integracao
 * =================================
 *
 * Responsabilidade TECNICA:
 * - Trata erros de integracao (ML, APIs externas)
 * - Registra incidente e notifica equipe
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - delegate_erro (String): Mensagem de erro
 *
 * OUTPUT (variaveis criadas):
 * - erro_tratado (Boolean): Se erro foi tratado
 * - erro_tipo (String): Tipo do erro
 * - erro_incidente_id (String): ID do incidente criado
 */
@Component("tratarErroDelegate")
public class TratarErroDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(TratarErroDelegate.class);

    @Autowired
    private NotificacaoService notificacaoService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.error("[{}] Tratando erro de integracao - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getOptionalVariable(execution, "beneficiario_cpf", String.class, "");
            String erroMensagem = getOptionalVariable(execution, "delegate_erro", String.class, "Erro desconhecido");
            String erroStatus = getOptionalVariable(execution, "delegate_status", String.class, "ERRO");

            // 2. EXECUTAR logica tecnica
            // Gera ID do incidente
            String incidenteId = "INC-" + System.currentTimeMillis();

            logger.error("[{}] Incidente criado: {} - Erro: {}", activityId, incidenteId, erroMensagem);

            // Notifica equipe de suporte
            notificacaoService.notificarEquipe("ERRO_INTEGRACAO",
                String.format("Incidente %s - Processo: %s - CPF: %s - Erro: %s",
                    incidenteId, processInstanceId, cpf, erroMensagem));

            // 3. ESCREVER variaveis de saida
            execution.setVariable("erro_tratado", true);
            execution.setVariable("erro_tipo", erroStatus);
            execution.setVariable("erro_incidente_id", incidenteId);
            execution.setVariable("erro_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "ERRO_TRATADO");

            logger.info("[{}] Erro tratado - Incidente: {}", activityId, incidenteId);

        } catch (Exception e) {
            logger.error("[{}] Erro ao tratar erro (meta-erro): {}", activityId, e.getMessage(), e);
            execution.setVariable("erro_tratado", false);
            execution.setVariable("delegate_status", "ERRO_CRITICO");
            // Nao relanca excecao - ja estamos no fluxo de erro
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T getOptionalVariable(DelegateExecution execution, String name, Class<T> type, T defaultValue) {
        Object value = execution.getVariable(name);
        return value != null ? (T) value : defaultValue;
    }
}
