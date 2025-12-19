package com.operadora.delegates.onboarding;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.WhatsAppService;

/**
 * Delegate: Enviar Boas-Vindas WhatsApp
 * =====================================
 *
 * Responsabilidade TECNICA:
 * - Envia mensagem de boas-vindas via WhatsApp Business API
 * - Registra o envio no historico de comunicacoes
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_nome (String): Nome do beneficiario
 * - beneficiario_telefone (String): Telefone do beneficiario
 *
 * OUTPUT (variaveis criadas):
 * - boas_vindas_enviada (Boolean): Se mensagem foi enviada
 * - boas_vindas_message_id (String): ID da mensagem no WhatsApp
 * - boas_vindas_timestamp (String): Data/hora do envio
 */
@Component("enviarBoasVindasDelegate")
public class EnviarBoasVindasDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(EnviarBoasVindasDelegate.class);

    @Autowired
    private WhatsAppService whatsAppService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();
        String businessKey = execution.getBusinessKey();

        logger.info("[{}] Iniciando envio de boas-vindas - Process: {}, BusinessKey: {}",
                    activityId, processInstanceId, businessKey);

        try {
            // 1. LER variaveis de entrada
            String nome = getRequiredVariable(execution, "beneficiario_nome", String.class);
            String telefone = getRequiredVariable(execution, "beneficiario_telefone", String.class);

            logger.debug("[{}] Beneficiario: {} - Telefone: {}", activityId, nome, telefone);

            // 2. EXECUTAR logica tecnica
            String mensagem = String.format(
                "Ola %s! Bem-vindo(a) a Operadora Digital do Futuro! " +
                "Estamos muito felizes em te-lo(a) conosco. " +
                "Em breve, enviaremos um questionario rapido de saude para conhece-lo(a) melhor.",
                nome
            );

            WhatsAppService.SendResult resultado = whatsAppService.enviarMensagem(telefone, mensagem);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("boas_vindas_enviada", resultado.isSuccess());
            execution.setVariable("boas_vindas_message_id", resultado.getMessageId());
            execution.setVariable("boas_vindas_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Boas-vindas enviadas com sucesso - MessageID: {}",
                        activityId, resultado.getMessageId());

        } catch (Exception e) {
            logger.error("[{}] Erro ao enviar boas-vindas: {}", activityId, e.getMessage(), e);
            execution.setVariable("boas_vindas_enviada", false);
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
}
