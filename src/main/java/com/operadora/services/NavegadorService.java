package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Service: Navegador de Saude
 * ============================
 *
 * Gerencia atribuicao de navegadores para pacientes de alto risco.
 */
@Service
public class NavegadorService {

    private static final Logger logger = LoggerFactory.getLogger(NavegadorService.class);

    /**
     * Atribui navegador ao beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param nivelRisco Nivel de risco
     * @param fatoresRisco Fatores identificados
     * @return Navegador atribuido
     */
    public Navegador atribuirNavegador(String cpf, String nivelRisco, String fatoresRisco) {
        logger.info("Atribuindo navegador para CPF: {}, Risco: {}", cpf, nivelRisco);

        // MOCK: Em producao, buscar navegador com menor carga
        // e especialidade adequada aos fatores de risco

        Navegador navegador = new Navegador();

        // Seleciona especialidade baseada nos fatores
        String especialidade = "CLINICO_GERAL";
        if (fatoresRisco.contains("DIABETES") || fatoresRisco.contains("DOENCA_CRONICA")) {
            especialidade = "CRONICO";
        } else if (fatoresRisco.contains("IDADE_AVANCADA")) {
            especialidade = "GERIATRIA";
        } else if (fatoresRisco.contains("ONCOLOGIA")) {
            especialidade = "ONCOLOGIA";
        }

        // Simula navegador disponivel
        navegador.setId("NAV-" + System.currentTimeMillis() % 1000);
        navegador.setNome("Maria Navegadora");
        navegador.setTelefone("11999888777");
        navegador.setEspecialidade(especialidade);
        navegador.setEmail("maria.navegadora@operadora.com");

        logger.info("Navegador atribuido: {} - Especialidade: {}", navegador.getNome(), especialidade);

        return navegador;
    }

    /**
     * Dados do navegador.
     */
    public static class Navegador {
        private String id;
        private String nome;
        private String telefone;
        private String email;
        private String especialidade;

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getNome() { return nome; }
        public void setNome(String nome) { this.nome = nome; }

        public String getTelefone() { return telefone; }
        public void setTelefone(String telefone) { this.telefone = telefone; }

        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }

        public String getEspecialidade() { return especialidade; }
        public void setEspecialidade(String especialidade) { this.especialidade = especialidade; }
    }
}
