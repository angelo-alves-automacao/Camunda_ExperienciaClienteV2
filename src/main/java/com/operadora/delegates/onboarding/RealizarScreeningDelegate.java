package com.operadora.delegates.onboarding;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.ScreeningService;

/**
 * Delegate: Realizar Screening de Saude
 * ======================================
 *
 * Responsabilidade TECNICA:
 * - Coleta respostas do questionario de saude
 * - Calcula score inicial de risco
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_id (String): ID do beneficiario
 * - beneficiario_cpf (String): CPF do beneficiario
 *
 * OUTPUT (variaveis criadas):
 * - screening_completo (Boolean): Se screening foi completado
 * - screening_score (Integer): Score de 0-100
 * - idade (Integer): Idade do beneficiario
 * - tem_doenca_cronica (Boolean): Se tem doenca cronica
 * - imc (Double): Indice de Massa Corporal
 * - respostas_screening (Object): JSON com todas as respostas
 */
@Component("realizarScreeningDelegate")
public class RealizarScreeningDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(RealizarScreeningDelegate.class);

    @Autowired
    private ScreeningService screeningService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando screening de saude - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String beneficiarioId = getOptionalVariable(execution, "beneficiario_id", String.class, "");
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);

            // 2. EXECUTAR logica tecnica
            ScreeningService.ScreeningResult resultado = screeningService.realizarScreening(cpf);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("screening_completo", true);
            execution.setVariable("screening_score", resultado.getScore());
            execution.setVariable("idade", resultado.getIdade());
            execution.setVariable("tem_doenca_cronica", resultado.isTemDoencaCronica());
            execution.setVariable("imc", resultado.getImc());
            execution.setVariable("fumante", resultado.isFumante());
            execution.setVariable("pratica_exercicio", resultado.isPraticaExercicio());
            execution.setVariable("respostas_screening", resultado.getRespostasJson());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Screening concluido - Score: {}, Idade: {}, Cronico: {}",
                        activityId, resultado.getScore(), resultado.getIdade(), resultado.isTemDoencaCronica());

        } catch (Exception e) {
            logger.error("[{}] Erro no screening: {}", activityId, e.getMessage(), e);
            execution.setVariable("screening_completo", false);
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
