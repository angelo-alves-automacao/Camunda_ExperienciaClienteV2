package com.operadora.delegates.followup;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.FollowupService;

/**
 * Delegate: Follow-up Pos-Atendimento
 * ====================================
 *
 * Responsabilidade TECNICA:
 * - Realiza follow-up apos atendimentos
 * - Verifica satisfacao e resultados clinicos
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - beneficiario_nome (String): Nome
 * - beneficiario_telefone (String): Telefone
 * - jornada_id (String): ID da jornada (se houver)
 *
 * OUTPUT (variaveis criadas):
 * - followup_realizado (Boolean): Se follow-up foi feito
 * - followup_resposta (String): Resposta do beneficiario
 * - followup_satisfacao (Integer): Score de 1-5
 */
@Component("followupPosDelegate")
public class FollowupPosDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(FollowupPosDelegate.class);

    @Autowired
    private FollowupService followupService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando follow-up pos-atendimento - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String nome = getRequiredVariable(execution, "beneficiario_nome", String.class);
            String telefone = getRequiredVariable(execution, "beneficiario_telefone", String.class);
            String jornadaId = getOptionalVariable(execution, "jornada_id", String.class, null);

            // 2. EXECUTAR logica tecnica
            FollowupService.FollowupResult resultado = followupService.realizarFollowup(cpf, nome, telefone, jornadaId);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("followup_realizado", true);
            execution.setVariable("followup_resposta", resultado.getResposta());
            execution.setVariable("followup_satisfacao", resultado.getSatisfacao());
            execution.setVariable("followup_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Follow-up realizado - Satisfacao: {}/5", activityId, resultado.getSatisfacao());

        } catch (Exception e) {
            logger.error("[{}] Erro no follow-up: {}", activityId, e.getMessage(), e);
            execution.setVariable("followup_realizado", false);
            execution.setVariable("delegate_status", "ERRO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw e;
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
