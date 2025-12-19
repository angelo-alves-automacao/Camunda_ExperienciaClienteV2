package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Arrays;
import java.util.List;

/**
 * Service: Jornada do Paciente
 * =============================
 *
 * Gerencia a jornada completa do paciente de alto risco.
 */
@Service
public class JornadaService {

    private static final Logger logger = LoggerFactory.getLogger(JornadaService.class);

    /**
     * Cria jornada para o beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param navegadorId ID do navegador responsavel
     * @param prestadorId ID do prestador
     * @param fatoresRisco Fatores de risco
     * @return Jornada criada
     */
    public Jornada criarJornada(String cpf, String navegadorId, String prestadorId, String fatoresRisco) {
        logger.info("Criando jornada para CPF: {}, Navegador: {}", cpf, navegadorId);

        Jornada jornada = new Jornada();

        jornada.setId("JRN-" + System.currentTimeMillis());
        jornada.setStatus("EM_ACOMPANHAMENTO");
        jornada.setDataInicio(Instant.now().toString());

        // Define etapas baseadas nos fatores de risco
        List<String> etapas = definirEtapas(fatoresRisco);
        jornada.setEtapas(etapas);
        jornada.setProximaEtapa(etapas.get(0));

        logger.info("Jornada criada: {} - Etapas: {}", jornada.getId(), etapas.size());

        return jornada;
    }

    private List<String> definirEtapas(String fatoresRisco) {
        // Define etapas padrao
        if (fatoresRisco.contains("DOENCA_CRONICA")) {
            return Arrays.asList(
                "CONSULTA_ESPECIALISTA",
                "EXAMES_LABORATORIAIS",
                "RETORNO_MEDICO",
                "ACOMPANHAMENTO_MENSAL"
            );
        } else if (fatoresRisco.contains("IDADE_AVANCADA")) {
            return Arrays.asList(
                "AVALIACAO_GERIATRICA",
                "EXAMES_PREVENTIVOS",
                "ORIENTACAO_FAMILIAR",
                "ACOMPANHAMENTO_QUINZENAL"
            );
        } else {
            return Arrays.asList(
                "CONSULTA_INICIAL",
                "EXAMES_COMPLEMENTARES",
                "PLANO_TRATAMENTO",
                "ACOMPANHAMENTO_SEMANAL"
            );
        }
    }

    /**
     * Dados da jornada.
     */
    public static class Jornada {
        private String id;
        private String status;
        private String dataInicio;
        private List<String> etapas;
        private String proximaEtapa;

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }

        public String getDataInicio() { return dataInicio; }
        public void setDataInicio(String dataInicio) { this.dataInicio = dataInicio; }

        public List<String> getEtapas() { return etapas; }
        public void setEtapas(List<String> etapas) { this.etapas = etapas; }

        public String getProximaEtapa() { return proximaEtapa; }
        public void setProximaEtapa(String proximaEtapa) { this.proximaEtapa = proximaEtapa; }
    }
}
