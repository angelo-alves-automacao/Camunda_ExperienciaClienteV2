-- =============================================================================
-- MVP Camunda - Estrutura Oracle para Autorização Cirúrgica
-- =============================================================================
-- Este script cria as tabelas necessárias para o MVP
-- Adapte conforme a estrutura real do Tasy em seu ambiente
-- =============================================================================

-- -----------------------------------------------------------------------------
-- SCHEMA: AUTOMACAO (para tabelas do processo de automação)
-- -----------------------------------------------------------------------------
-- CREATE USER automacao IDENTIFIED BY automacao_pwd;
-- GRANT CONNECT, RESOURCE TO automacao;
-- GRANT CREATE TABLE, CREATE SEQUENCE, CREATE TRIGGER TO automacao;

-- -----------------------------------------------------------------------------
-- TABELA: Fila de Notificações para Médicos
-- Usada pelo External Task Worker para inserir notificações
-- O Trigger Oracle consolidará e enviará via WhatsApp
-- -----------------------------------------------------------------------------
CREATE TABLE automacao.fila_notificacao_medico (
    nr_sequencia          NUMBER(18)    PRIMARY KEY,
    cd_crm_medico         VARCHAR2(20)  NOT NULL,
    nm_paciente           VARCHAR2(200) NOT NULL,
    nr_autorizacao        VARCHAR2(50),
    ie_status_autorizacao VARCHAR2(20)  NOT NULL,
    ds_mensagem           VARCHAR2(4000),
    ie_status_envio       VARCHAR2(20)  DEFAULT 'PENDENTE' NOT NULL,
    dt_criacao            DATE          DEFAULT SYSDATE NOT NULL,
    dt_envio_previsto     DATE,
    dt_envio_realizado    DATE,
    ds_erro_envio         VARCHAR2(4000),
    CONSTRAINT chk_status_envio CHECK (ie_status_envio IN ('PENDENTE', 'ENVIADO', 'ERRO', 'CANCELADO'))
);

-- Índices para performance
CREATE INDEX idx_notif_medico_crm ON automacao.fila_notificacao_medico(cd_crm_medico);
CREATE INDEX idx_notif_status ON automacao.fila_notificacao_medico(ie_status_envio);
CREATE INDEX idx_notif_dt_previsto ON automacao.fila_notificacao_medico(dt_envio_previsto);

-- Sequence
CREATE SEQUENCE automacao.seq_notificacao START WITH 1 INCREMENT BY 1;

-- Comentários
COMMENT ON TABLE automacao.fila_notificacao_medico IS 'Fila de notificações para médicos - processada pelo Trigger Oracle para envio consolidado via WhatsApp';
COMMENT ON COLUMN automacao.fila_notificacao_medico.ie_status_envio IS 'PENDENTE=aguardando envio, ENVIADO=enviado com sucesso, ERRO=falha no envio, CANCELADO=cancelado manualmente';


-- -----------------------------------------------------------------------------
-- TABELA: Autorizações Cirúrgicas (se não existir no Tasy)
-- Complementar à estrutura do Tasy
-- -----------------------------------------------------------------------------
CREATE TABLE tasy.autorizacao_cirurgica (
    nr_sequencia        NUMBER(18)    PRIMARY KEY,
    nr_seq_paciente     NUMBER(18)    NOT NULL,
    nr_autorizacao      VARCHAR2(50)  NOT NULL,
    dt_autorizacao      DATE          NOT NULL,
    ie_status           VARCHAR2(20)  NOT NULL,
    cd_convenio         VARCHAR2(20),
    cd_procedimento     VARCHAR2(20),
    dt_atualizacao      DATE          DEFAULT SYSDATE,
    nm_usuario          VARCHAR2(100),
    CONSTRAINT fk_autorizacao_paciente FOREIGN KEY (nr_seq_paciente) 
        REFERENCES tasy.paciente(nr_sequencia)
);

-- Índices
CREATE INDEX idx_autor_paciente ON tasy.autorizacao_cirurgica(nr_seq_paciente);
CREATE INDEX idx_autor_numero ON tasy.autorizacao_cirurgica(nr_autorizacao);
CREATE INDEX idx_autor_status ON tasy.autorizacao_cirurgica(ie_status);

-- Sequence
CREATE SEQUENCE tasy.seq_autorizacao START WITH 1 INCREMENT BY 1;


-- -----------------------------------------------------------------------------
-- TRIGGER: Consolidação e Envio de Notificações
-- Executa diariamente às 18h para enviar resumo consolidado
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE automacao.proc_enviar_notificacoes_consolidadas AS
    v_crm_atual     VARCHAR2(20);
    v_mensagem      CLOB;
    v_total_guias   NUMBER;
    v_telefone      VARCHAR2(20);
    v_resultado     VARCHAR2(100);
    
    -- Cursor para médicos com notificações pendentes
    CURSOR c_medicos IS
        SELECT DISTINCT cd_crm_medico
        FROM automacao.fila_notificacao_medico
        WHERE ie_status_envio = 'PENDENTE'
          AND dt_envio_previsto <= SYSDATE;
    
    -- Cursor para notificações de um médico específico
    CURSOR c_notificacoes(p_crm VARCHAR2) IS
        SELECT nr_sequencia, nm_paciente, nr_autorizacao, ie_status_autorizacao
        FROM automacao.fila_notificacao_medico
        WHERE cd_crm_medico = p_crm
          AND ie_status_envio = 'PENDENTE'
          AND dt_envio_previsto <= SYSDATE
        ORDER BY dt_criacao;
        
BEGIN
    -- Para cada médico com notificações pendentes
    FOR r_medico IN c_medicos LOOP
        v_crm_atual := r_medico.cd_crm_medico;
        v_mensagem := '';
        v_total_guias := 0;
        
        -- Busca telefone do médico (adaptar conforme estrutura real)
        BEGIN
            SELECT nr_telefone_celular
            INTO v_telefone
            FROM tasy.medico
            WHERE cd_crm = v_crm_atual;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_telefone := NULL;
        END;
        
        -- Se não tem telefone, marca como erro e pula
        IF v_telefone IS NULL THEN
            UPDATE automacao.fila_notificacao_medico
            SET ie_status_envio = 'ERRO',
                ds_erro_envio = 'Telefone do médico não cadastrado',
                dt_envio_realizado = SYSDATE
            WHERE cd_crm_medico = v_crm_atual
              AND ie_status_envio = 'PENDENTE';
            CONTINUE;
        END IF;
        
        -- Monta mensagem consolidada
        v_mensagem := '🏥 *Resumo de Autorizações - Hospital AUSTA*' || CHR(10) || CHR(10);
        
        FOR r_notif IN c_notificacoes(v_crm_atual) LOOP
            v_total_guias := v_total_guias + 1;
            v_mensagem := v_mensagem || 
                '📋 ' || r_notif.nm_paciente || CHR(10) ||
                '   Autorização: ' || NVL(r_notif.nr_autorizacao, 'Pendente') || CHR(10) ||
                '   Status: ' || r_notif.ie_status_autorizacao || CHR(10) || CHR(10);
        END LOOP;
        
        v_mensagem := v_mensagem || 
            '─────────────────' || CHR(10) ||
            'Total de guias: ' || v_total_guias || CHR(10) ||
            'Data: ' || TO_CHAR(SYSDATE, 'DD/MM/YYYY HH24:MI');
        
        -- Chama API de envio WhatsApp (implementar conforme sua integração)
        -- v_resultado := automacao.pkg_whatsapp.enviar_mensagem(v_telefone, v_mensagem);
        
        -- Por enquanto, simula sucesso
        v_resultado := 'SUCESSO';
        
        -- Atualiza status das notificações
        IF v_resultado = 'SUCESSO' THEN
            UPDATE automacao.fila_notificacao_medico
            SET ie_status_envio = 'ENVIADO',
                dt_envio_realizado = SYSDATE
            WHERE cd_crm_medico = v_crm_atual
              AND ie_status_envio = 'PENDENTE'
              AND dt_envio_previsto <= SYSDATE;
        ELSE
            UPDATE automacao.fila_notificacao_medico
            SET ie_status_envio = 'ERRO',
                ds_erro_envio = v_resultado,
                dt_envio_realizado = SYSDATE
            WHERE cd_crm_medico = v_crm_atual
              AND ie_status_envio = 'PENDENTE'
              AND dt_envio_previsto <= SYSDATE;
        END IF;
        
        COMMIT;
    END LOOP;
    
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END;
/


-- -----------------------------------------------------------------------------
-- JOB: Agendamento do envio consolidado (Oracle Scheduler)
-- -----------------------------------------------------------------------------
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'AUTOMACAO.JOB_NOTIFICACAO_MEDICOS',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'AUTOMACAO.PROC_ENVIAR_NOTIFICACOES_CONSOLIDADAS',
        start_date      => TRUNC(SYSDATE) + 18/24,  -- Hoje às 18h
        repeat_interval => 'FREQ=DAILY; BYHOUR=18; BYMINUTE=0; BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Envia notificações consolidadas para médicos via WhatsApp'
    );
END;
/


-- -----------------------------------------------------------------------------
-- VIEW: Monitoramento de Notificações
-- Para uso no Metabase ou dashboards
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW automacao.vw_monitor_notificacoes AS
SELECT 
    TRUNC(dt_criacao) AS data_criacao,
    cd_crm_medico,
    ie_status_envio,
    COUNT(*) AS total_notificacoes,
    MIN(dt_criacao) AS primeira_notificacao,
    MAX(dt_criacao) AS ultima_notificacao
FROM 
    automacao.fila_notificacao_medico
GROUP BY 
    TRUNC(dt_criacao),
    cd_crm_medico,
    ie_status_envio;


-- -----------------------------------------------------------------------------
-- GRANTS (ajustar conforme necessário)
-- -----------------------------------------------------------------------------
-- GRANT SELECT, INSERT ON automacao.fila_notificacao_medico TO camunda_user;
-- GRANT SELECT, INSERT ON tasy.autorizacao_cirurgica TO camunda_user;
-- GRANT SELECT ON automacao.vw_monitor_notificacoes TO metabase_user;
