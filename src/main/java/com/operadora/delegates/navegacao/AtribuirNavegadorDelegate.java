package com.operadora.delegates.navegacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.NavegadorService;

/**
 * Delegate: Atribuir Navegador
 * =============================
 *
 * Responsabilidade TECNICA:
 * - Atribui um navegador de saude dedicado ao paciente
 * - Considera especialidade necessaria e carga de trabalho
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - nivel_risco (String): ALTO ou COMPLEXO
 * - fatores_risco (String): Fatores identificados
 *
 * OUTPUT (variaveis criadas):
 * - navegador_id (String): ID do navegador atribuido
 * - navegador_nome (String): Nome do navegador
 * - navegador_telefone (String): Telefone do navegador
 * - navegador_especialidade (String): Especialidade do navegador
 */
@Component("atribuirNavegadorDelegate")
public class AtribuirNavegadorDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(AtribuirNavegadorDelegate.class);

    @Autowired
    private NavegadorService navegadorService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando atribuicao de navegador - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String nivelRisco = getRequiredVariable(execution, "nivel_risco", String.class);
            String fatoresRisco = getOptionalVariable(execution, "fatores_risco", String.class, "");

            // 2. EXECUTAR logica tecnica
            NavegadorService.Navegador navegador = navegadorService.atribuirNavegador(cpf, nivelRisco, fatoresRisco);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("navegador_id", navegador.getId());
            execution.setVariable("navegador_nome", navegador.getNome());
            execution.setVariable("navegador_telefone", navegador.getTelefone());
            execution.setVariable("navegador_especialidade", navegador.getEspecialidade());
            execution.setVariable("navegador_atribuido", true);
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Navegador atribuido - ID: {}, Nome: {}, Especialidade: {}",
                        activityId, navegador.getId(), navegador.getNome(), navegador.getEspecialidade());

        } catch (Exception e) {
            logger.error("[{}] Erro ao atribuir navegador: {}", activityId, e.getMessage(), e);
            execution.setVariable("navegador_atribuido", false);
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
