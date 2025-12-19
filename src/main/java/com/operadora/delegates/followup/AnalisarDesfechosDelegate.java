package com.operadora.delegates.followup;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.AnalyticsService;

/**
 * Delegate: Analisar Desfechos
 * =============================
 *
 * Responsabilidade TECNICA:
 * - Analisa desfechos clinicos e operacionais
 * - Registra metricas para machine learning
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - nivel_risco (String): Nivel de risco do beneficiario
 * - nps_score (Integer): Score NPS coletado
 * - jornada_id (String): ID da jornada (se houver)
 *
 * OUTPUT (variaveis criadas):
 * - desfecho_categoria (String): POSITIVO, NEUTRO, NEGATIVO
 * - desfecho_metricas (Object): Metricas coletadas
 * - ciclo_completo (Boolean): Se ciclo foi finalizado
 */
@Component("analisarDesfechosDelegate")
public class AnalisarDesfechosDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(AnalisarDesfechosDelegate.class);

    @Autowired
    private AnalyticsService analyticsService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando analise de desfechos - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String nivelRisco = getOptionalVariable(execution, "nivel_risco", String.class, "BAIXO");
            Integer npsScore = getOptionalVariable(execution, "nps_score", Integer.class, 7);
            String jornadaId = getOptionalVariable(execution, "jornada_id", String.class, null);

            // 2. EXECUTAR logica tecnica
            AnalyticsService.DesfechoResult resultado = analyticsService.analisarDesfechos(
                cpf, nivelRisco, npsScore, jornadaId, processInstanceId
            );

            // 3. ESCREVER variaveis de saida
            execution.setVariable("desfecho_categoria", resultado.getCategoria());
            execution.setVariable("desfecho_metricas", resultado.getMetricasJson());
            execution.setVariable("desfecho_recomendacoes", resultado.getRecomendacoes());
            execution.setVariable("ciclo_completo", true);
            execution.setVariable("ciclo_data_fim", java.time.Instant.now().toString());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Desfechos analisados - Categoria: {}, Ciclo completo",
                        activityId, resultado.getCategoria());

        } catch (Exception e) {
            logger.error("[{}] Erro na analise de desfechos: {}", activityId, e.getMessage(), e);
            execution.setVariable("ciclo_completo", false);
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
