package com.operadora.delegates.onboarding;

import org.camunda.bpm.engine.delegate.BpmnError;
import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.MLService;

/**
 * Delegate: Estratificar Risco (ML)
 * ==================================
 *
 * Responsabilidade TECNICA:
 * - Chama modelo de ML (XGBoost) para calcular risco
 * - Classifica na piramide Kaiser (BAIXO, MODERADO, ALTO, COMPLEXO)
 *
 * INPUT (variaveis esperadas):
 * - screening_score (Integer): Score do screening
 * - idade (Integer): Idade do beneficiario
 * - tem_doenca_cronica (Boolean): Se tem doenca cronica
 * - imc (Double): IMC calculado
 * - fumante (Boolean): Se e fumante
 *
 * OUTPUT (variaveis criadas):
 * - nivel_risco (String): BAIXO, MODERADO, ALTO, COMPLEXO
 * - score_risco (Double): Score de 0.0 a 1.0
 * - probabilidade_internacao (Double): Prob. de internacao em 12 meses
 * - fatores_risco (String): Lista de fatores identificados
 *
 * ERROS (BpmnError):
 * - ERRO_INTEGRACAO: Falha na chamada ao servico ML
 */
@Component("estratificarRiscoDelegate")
public class EstratificarRiscoDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(EstratificarRiscoDelegate.class);

    private static final String ERRO_INTEGRACAO = "ERRO_INTEGRACAO";

    @Autowired
    private MLService mlService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando estratificacao de risco - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            Integer screeningScore = getOptionalVariable(execution, "screening_score", Integer.class, 50);
            Integer idade = getRequiredVariable(execution, "idade", Integer.class);
            Boolean temDoencaCronica = getOptionalVariable(execution, "tem_doenca_cronica", Boolean.class, false);
            Double imc = getOptionalVariable(execution, "imc", Double.class, 25.0);
            Boolean fumante = getOptionalVariable(execution, "fumante", Boolean.class, false);

            logger.debug("[{}] Dados para ML - Score: {}, Idade: {}, Cronico: {}, IMC: {}, Fumante: {}",
                        activityId, screeningScore, idade, temDoencaCronica, imc, fumante);

            // 2. EXECUTAR logica tecnica (chamada ao modelo ML)
            MLService.RiskResult resultado = mlService.calcularRisco(
                screeningScore, idade, temDoencaCronica, imc, fumante
            );

            // 3. ESCREVER variaveis de saida
            execution.setVariable("nivel_risco", resultado.getNivelRisco());
            execution.setVariable("score_risco", resultado.getScoreRisco());
            execution.setVariable("probabilidade_internacao", resultado.getProbabilidadeInternacao());
            execution.setVariable("fatores_risco", resultado.getFatoresRisco());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Estratificacao concluida - Nivel: {}, Score: {:.2f}",
                        activityId, resultado.getNivelRisco(), resultado.getScoreRisco());

        } catch (MLService.MLServiceException e) {
            logger.error("[{}] Erro de integracao ML: {}", activityId, e.getMessage(), e);
            execution.setVariable("delegate_status", "ERRO_INTEGRACAO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw new BpmnError(ERRO_INTEGRACAO, "Falha na estratificacao ML: " + e.getMessage());

        } catch (Exception e) {
            logger.error("[{}] Erro inesperado: {}", activityId, e.getMessage(), e);
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
