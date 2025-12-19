package com.operadora.delegates.comunicacao;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.operadora.services.MonitoramentoService;

/**
 * Delegate: Monitoramento Proativo
 * =================================
 *
 * Responsabilidade TECNICA:
 * - Verifica gatilhos de saude do beneficiario
 * - Identifica acoes preventivas necessarias
 *
 * INPUT (variaveis esperadas):
 * - beneficiario_cpf (String): CPF do beneficiario
 * - nivel_risco (String): Nivel de risco atual
 * - plano_cuidados (Object): Plano definido pelo DMN
 *
 * OUTPUT (variaveis criadas):
 * - gatilhos_identificados (String[]): Lista de gatilhos
 * - acoes_preventivas (String[]): Lista de acoes
 * - requer_contato_imediato (Boolean): Se precisa contato urgente
 */
@Component("monitoramentoProativoDelegate")
public class MonitoramentoProativoDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(MonitoramentoProativoDelegate.class);

    @Autowired
    private MonitoramentoService monitoramentoService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando monitoramento proativo - Process: {}", activityId, processInstanceId);

        try {
            // 1. LER variaveis de entrada
            String cpf = getRequiredVariable(execution, "beneficiario_cpf", String.class);
            String nivelRisco = getRequiredVariable(execution, "nivel_risco", String.class);

            // 2. EXECUTAR logica tecnica
            MonitoramentoService.MonitoramentoResult resultado =
                monitoramentoService.verificarGatilhos(cpf, nivelRisco);

            // 3. ESCREVER variaveis de saida
            execution.setVariable("gatilhos_identificados", resultado.getGatilhos());
            execution.setVariable("acoes_preventivas", resultado.getAcoesPreventivas());
            execution.setVariable("requer_contato_imediato", resultado.isRequerContatoImediato());
            execution.setVariable("proxima_acao", resultado.getProximaAcao());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Monitoramento concluido - Gatilhos: {}, Contato imediato: {}",
                        activityId, resultado.getGatilhos().size(), resultado.isRequerContatoImediato());

        } catch (Exception e) {
            logger.error("[{}] Erro no monitoramento: {}", activityId, e.getMessage(), e);
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
