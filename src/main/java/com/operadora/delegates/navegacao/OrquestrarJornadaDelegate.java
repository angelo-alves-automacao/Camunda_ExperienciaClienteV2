package com.operadora.delegates.navegacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.JornadaService;

/**
 * Delegate: Orquestrar Jornada
 * =============================
 *
 * Responsabilidade TECNICA:
 * - Coordena a jornada completa do paciente de alto risco
 * - Cria cronograma de consultas, exames e procedimentos
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - navegador_id (String): ID do navegador responsavel
 * - rede_prestador_id (String): ID do prestador selecionado
 * - fatores_risco (String): Fatores de risco
 *
 * OUTPUT (variaveis criadas):
 * - jornada_id (String): ID da jornada criada
 * - jornada_status (String): Status atual
 * - jornada_etapas (String[]): Lista de etapas
 * - jornada_proxima_etapa (String): Proxima etapa
 */
@Component("orquestrarJornadaDelegate")
public class OrquestrarJornadaDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(OrquestrarJornadaDelegate.class);

    @Autowired
    private JornadaService jornadaService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando orquestracao de jornada - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String navegadorId = getRequiredVariable(execution, "navegador_id", String.class);
            String prestadorId = getOptionalVariable(execution, "rede_prestador_id", String.class, "");
            String fatoresRisco = getOptionalVariable(execution, "fatores_risco", String.class, "");

            // 2. EXECUTAR logica tecnica
            JornadaService.Jornada jornada = jornadaService.criarJornada(cpf, navegadorId, prestadorId, fatoresRisco);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("jornada_id", jornada.getId());
            execution.setVariable("jornada_status", jornada.getStatus());
            execution.setVariable("jornada_etapas", jornada.getEtapas());
            execution.setVariable("jornada_proxima_etapa", jornada.getProximaEtapa());
            execution.setVariable("jornada_data_inicio", jornada.getDataInicio());
            execution.setVariable("jornada_criada", true);
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Jornada criada - ID: {}, Etapas: {}, Proxima: {}",
                        activityId, jornada.getId(), jornada.getEtapas().size(), jornada.getProximaEtapa());

        } catch (Exception e) {
            logger.error("[{}] Erro ao orquestrar jornada: {}", activityId, e.getMessage(), e);
            execution.setVariable("jornada_criada", false);
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
