package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * Service: Monitoramento Proativo
 * ================================
 *
 * Verifica gatilhos de saude e acoes preventivas.
 */
@Service
public class MonitoramentoService {

    private static final Logger logger = LoggerFactory.getLogger(MonitoramentoService.class);

    /**
     * Verifica gatilhos de saude do beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param nivelRisco Nivel de risco atual
     * @return Resultado do monitoramento
     */
    public MonitoramentoResult verificarGatilhos(String cpf, String nivelRisco) {
        logger.info("Verificando gatilhos para CPF: {}, Risco: {}", cpf, nivelRisco);

        MonitoramentoResult resultado = new MonitoramentoResult();

        // MOCK: Em producao, consultar base de dados e regras de negocio
        List<String> gatilhos = new ArrayList<>();
        List<String> acoes = new ArrayList<>();
        boolean requerContato = false;
        String proximaAcao = "LEMBRETE_SAUDE";

        // Simula gatilhos baseados no nivel de risco
        switch (nivelRisco) {
            case "BAIXO":
                gatilhos.add("VACINA_PENDENTE");
                acoes.add("Enviar lembrete de vacina");
                proximaAcao = "VACINA";
                break;

            case "MODERADO":
                gatilhos.add("CHECKUP_VENCIDO");
                gatilhos.add("EXAME_LABORATORIAL");
                acoes.add("Agendar checkup anual");
                acoes.add("Solicitar exames de rotina");
                proximaAcao = "CHECKUP";
                break;

            case "ALTO":
            case "COMPLEXO":
                gatilhos.add("ACOMPANHAMENTO_CONTINUO");
                gatilhos.add("MEDICAMENTO_RENOVACAO");
                acoes.add("Contato com navegador");
                acoes.add("Verificar adesao ao tratamento");
                requerContato = true;
                proximaAcao = "MEDICAMENTO";
                break;

            default:
                gatilhos.add("BOAS_VINDAS");
                acoes.add("Enviar mensagem de boas-vindas");
                proximaAcao = "LEMBRETE_SAUDE";
        }

        resultado.setGatilhos(gatilhos);
        resultado.setAcoesPreventivas(acoes);
        resultado.setRequerContatoImediato(requerContato);
        resultado.setProximaAcao(proximaAcao);

        logger.info("Gatilhos identificados: {}", gatilhos.size());

        return resultado;
    }

    /**
     * Resultado do monitoramento.
     */
    public static class MonitoramentoResult {
        private List<String> gatilhos = new ArrayList<>();
        private List<String> acoesPreventivas = new ArrayList<>();
        private boolean requerContatoImediato;
        private String proximaAcao;

        public List<String> getGatilhos() { return gatilhos; }
        public void setGatilhos(List<String> gatilhos) { this.gatilhos = gatilhos; }

        public List<String> getAcoesPreventivas() { return acoesPreventivas; }
        public void setAcoesPreventivas(List<String> acoesPreventivas) { this.acoesPreventivas = acoesPreventivas; }

        public boolean isRequerContatoImediato() { return requerContatoImediato; }
        public void setRequerContatoImediato(boolean requerContatoImediato) {
            this.requerContatoImediato = requerContatoImediato;
        }

        public String getProximaAcao() { return proximaAcao; }
        public void setProximaAcao(String proximaAcao) { this.proximaAcao = proximaAcao; }
    }
}
