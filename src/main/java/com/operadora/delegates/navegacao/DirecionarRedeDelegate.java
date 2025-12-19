package com.operadora.delegates.navegacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.RedeCredenciadaService;

/**
 * Delegate: Direcionar Rede Preferencial
 * =======================================
 *
 * Responsabilidade TECNICA:
 * - Identifica a melhor rede credenciada para o paciente
 * - Considera localizacao, especialidade e qualidade
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - fatores_risco (String): Fatores de risco identificados
 * - navegador_especialidade (String): Especialidade do navegador
 *
 * OUTPUT (variaveis criadas):
 * - rede_prestador_id (String): ID do prestador selecionado
 * - rede_prestador_nome (String): Nome do prestador
 * - rede_prestador_endereco (String): Endereco
 * - rede_prestador_telefone (String): Telefone
 * - rede_qualidade_score (Double): Score de qualidade
 */
@Component("direcionarRedeDelegate")
public class DirecionarRedeDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(DirecionarRedeDelegate.class);

    @Autowired
    private RedeCredenciadaService redeService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando direcionamento para rede - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String fatoresRisco = getOptionalVariable(execution, "fatores_risco", String.class, "");
            String especialidade = getOptionalVariable(execution, "navegador_especialidade", String.class, "CLINICO_GERAL");

            // 2. EXECUTAR logica tecnica
            RedeCredenciadaService.Prestador prestador = redeService.buscarMelhorPrestador(cpf, especialidade, fatoresRisco);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("rede_prestador_id", prestador.getId());
            execution.setVariable("rede_prestador_nome", prestador.getNome());
            execution.setVariable("rede_prestador_endereco", prestador.getEndereco());
            execution.setVariable("rede_prestador_telefone", prestador.getTelefone());
            execution.setVariable("rede_qualidade_score", prestador.getQualidadeScore());
            execution.setVariable("rede_direcionada", true);
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Rede direcionada - Prestador: {}, Score: {:.2f}",
                        activityId, prestador.getNome(), prestador.getQualidadeScore());

        } catch (Exception e) {
            logger.error("[{}] Erro ao direcionar rede: {}", activityId, e.getMessage(), e);
            execution.setVariable("rede_direcionada", false);
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
