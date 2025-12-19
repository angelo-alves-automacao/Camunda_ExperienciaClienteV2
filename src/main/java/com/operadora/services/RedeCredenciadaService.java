package com.operadora.services;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Service: Rede Credenciada
 * ==========================
 *
 * Gerencia busca e direcionamento para rede credenciada.
 */
@Service
public class RedeCredenciadaService {

    private static final Logger logger = LoggerFactory.getLogger(RedeCredenciadaService.class);

    /**
     * Busca melhor prestador para o beneficiario.
     *
     * @param cpf CPF do beneficiario
     * @param especialidade Especialidade necessaria
     * @param fatoresRisco Fatores de risco
     * @return Prestador selecionado
     */
    public Prestador buscarMelhorPrestador(String cpf, String especialidade, String fatoresRisco) {
        logger.info("Buscando prestador para CPF: {}, Especialidade: {}", cpf, especialidade);

        // MOCK: Em producao, consultar base de rede credenciada
        // considerando localizacao, qualidade e disponibilidade

        Prestador prestador = new Prestador();

        prestador.setId("PREST-" + System.currentTimeMillis() % 10000);
        prestador.setNome("Hospital Sao Lucas");
        prestador.setEndereco("Av. Paulista, 1000 - Sao Paulo/SP");
        prestador.setTelefone("1133334444");
        prestador.setEspecialidades(especialidade);
        prestador.setQualidadeScore(4.5);

        logger.info("Prestador selecionado: {} - Score: {}", prestador.getNome(), prestador.getQualidadeScore());

        return prestador;
    }

    /**
     * Dados do prestador.
     */
    public static class Prestador {
        private String id;
        private String nome;
        private String endereco;
        private String telefone;
        private String especialidades;
        private double qualidadeScore;

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getNome() { return nome; }
        public void setNome(String nome) { this.nome = nome; }

        public String getEndereco() { return endereco; }
        public void setEndereco(String endereco) { this.endereco = endereco; }

        public String getTelefone() { return telefone; }
        public void setTelefone(String telefone) { this.telefone = telefone; }

        public String getEspecialidades() { return especialidades; }
        public void setEspecialidades(String especialidades) { this.especialidades = especialidades; }

        public double getQualidadeScore() { return qualidadeScore; }
        public void setQualidadeScore(double qualidadeScore) { this.qualidadeScore = qualidadeScore; }
    }
}
