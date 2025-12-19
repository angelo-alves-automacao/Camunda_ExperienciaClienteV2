package com.operadora.delegates.followup;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.NpsService;

/**
 * Delegate: Coletar NPS
 * ======================
 *
 * Responsabilidade TECNICA:
 * - Envia pesquisa NPS ao beneficiario
 * - Coleta e registra a resposta
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - beneficiario_nome (String): Nome
 * - beneficiario_telefone (String): Telefone
 *
 * OUTPUT (variaveis criadas):
 * - nps_enviado (Boolean): Se pesquisa foi enviada
 * - nps_score (Integer): Score de 0-10
 * - nps_categoria (String): DETRATOR, NEUTRO, PROMOTOR
 * - nps_comentario (String): Comentario livre
 */
@Component("coletarNpsDelegate")
public class ColetarNpsDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ColetarNpsDelegate.class);

    @Autowired
    private NpsService npsService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando coleta de NPS - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String nome = getRequiredVariable(execution, "beneficiario_nome", String.class);
            String telefone = getRequiredVariable(execution, "beneficiario_telefone", String.class);

            // 2. EXECUTAR logica tecnica
            NpsService.NpsResult resultado = npsService.coletarNps(cpf, nome, telefone);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("nps_enviado", true);
            execution.setVariable("nps_score", resultado.getScore());
            execution.setVariable("nps_categoria", resultado.getCategoria());
            execution.setVariable("nps_comentario", resultado.getComentario());
            execution.setVariable("nps_timestamp", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] NPS coletado - Score: {}, Categoria: {}",
                        activityId, resultado.getScore(), resultado.getCategoria());

        } catch (Exception e) {
            logger.error("[{}] Erro na coleta NPS: {}", activityId, e.getMessage(), e);
            execution.setVariable("nps_enviado", false);
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
