"""
External Task Worker: Oracle - Atualizar Autorização no Tasy
=============================================================

Responsabilidade TÉCNICA (não contém regras de negócio):
- Chamar procedures Oracle para atualizar autorização no Tasy
- Mapear status_autorizacao do RPA para nr_seq_estagio do Tasy
- Retornar status técnico ao processo

Procedures utilizadas:
1. TASY.RPA_ATUALIZA_AUTORIZACAO_CONV - Atualiza dados da guia
2. TASY.ATUALIZAR_AUTORIZACAO_CONVENIO - Atualiza estágio da autorização

O BPMN já definiu que esta tarefa deve ser executada.
O código NÃO decide caminhos do processo.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
import oracledb

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / '.env')

# Inicializa Oracle Client (modo thick) para suportar autenticação legada
# Requer Oracle Instant Client instalado
ORACLE_CLIENT_PATH = os.getenv("ORACLE_CLIENT_PATH", r"C:\oracle_client\instantclient_23_8")
try:
    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_PATH)
except Exception as e:
    logging.warning(f"Oracle Client não inicializado (modo thin): {e}")
from camunda.external_task.external_task import ExternalTask, TaskResult
from camunda.external_task.external_task_worker import ExternalTaskWorker

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
@dataclass
class OracleConfig:
    host: str = os.getenv("ORACLE_HOST", "localhost")
    port: int = int(os.getenv("ORACLE_PORT", "1521"))
    service_name: str = os.getenv("ORACLE_SERVICE_NAME", "TASY")
    user: str = os.getenv("ORACLE_USER", "tasy_user")
    password: str = os.getenv("ORACLE_PASSWORD", "tasy_pass")


@dataclass
class CamundaConfig:
    base_url: str = os.getenv("CAMUNDA_URL", "https://camundahml.austa.com.br/engine-rest")
    worker_id: str = "oracle-autorizacao-worker"
    max_tasks: int = 1
    lock_duration: int = 30000
    sleep_seconds: int = 5


# =============================================================================
# MAPEAMENTO DE STATUS PARA ESTÁGIO
# =============================================================================
# Mapeia status_autorizacao (retorno do RPA) para nr_seq_estagio_p (Tasy)
STATUS_PARA_ESTAGIO = {
    "Autorizado": 2,      # Aprovado
    "AUTORIZADO": 2,
    "Aprovado": 2,
    "APROVADO": 2,
    "Analise": 6,         # Análise/Auditoria
    "ANALISE": 6,
    "Auditoria": 29,      # Auditoria
    "AUDITORIA": 29,
    "Negado": 7,          # Negado
    "NEGADO": 7,
    "Recusado": 7,
    "RECUSADO": 7,
}

def obter_estagio_por_status(status_autorizacao: str) -> int:
    """
    Converte status_autorizacao do RPA para nr_seq_estagio do Tasy.

    Mapeamento:
    - Autorizado/Aprovado -> 2
    - Analise -> 6
    - Auditoria -> 29
    - Negado/Recusado -> 7

    Default: 6 (Análise) se status desconhecido
    """
    if not status_autorizacao:
        return 6  # Default: Análise

    return STATUS_PARA_ESTAGIO.get(status_autorizacao.strip(), 6)


# =============================================================================
# REPOSITÓRIO ORACLE - AUTORIZAÇÃO
# =============================================================================
class OracleAutorizacaoRepository:
    """
    Repositório para operações de autorização no Oracle/Tasy.
    Executa apenas operações técnicas de banco de dados.
    NÃO contém lógica de negócio.
    """

    def __init__(self, config: OracleConfig):
        self.config = config
        self._connection = None

    def _get_connection(self):
        """Obtém conexão com o Oracle."""
        if self._connection is None:
            dsn = oracledb.makedsn(
                self.config.host,
                self.config.port,
                service_name=self.config.service_name
            )
            self._connection = oracledb.connect(
                user=self.config.user,
                password=self.config.password,
                dsn=dsn
            )
        return self._connection

    def atualizar_autorizacao_guia(
        self,
        nr_sequencia: int,
        nr_guia_requisicao: str
    ) -> dict:
        """
        Atualiza dados da guia de autorização no Tasy.

        PROCEDURE: TASY.RPA_ATUALIZA_AUTORIZACAO_CONV

        Parâmetros:
        - p_nr_sequencia: Número sequencial da autorização
        - p_nm_usuario: Usuário da automação ('automacaotasy')
        - p_cd_senha: Código da guia (nr_guia_requisicao)
        - p_cd_autorizacao_prest: Código autorização prestador (nr_guia_requisicao)
        - p_cd_autorizacao: Código autorização (nr_guia_requisicao)
        - p_dt_validade_guia: Data de validade (SYSDATE + 1)
        """
        call_sql = """
            BEGIN
                TASY.RPA_ATUALIZA_AUTORIZACAO_CONV(
                    :p_nr_sequencia,
                    :p_nm_usuario,
                    :p_cd_senha,
                    :p_cd_autorizacao_prest,
                    :p_cd_autorizacao,
                    :p_dt_validade_guia
                );
            END;
        """

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Data de validade = amanhã
            dt_validade = datetime.now() + timedelta(days=1)

            logger.info(f"Chamando RPA_ATUALIZA_AUTORIZACAO_CONV - "
                       f"nr_sequencia: {nr_sequencia}, guia: {nr_guia_requisicao}")

            cursor.execute(call_sql, {
                'p_nr_sequencia': nr_sequencia,
                'p_nm_usuario': 'automacaotasy',
                'p_cd_senha': nr_guia_requisicao,
                'p_cd_autorizacao_prest': nr_guia_requisicao,
                'p_cd_autorizacao': nr_guia_requisicao,
                'p_dt_validade_guia': dt_validade
            })

            conn.commit()

            logger.info(f"Procedure RPA_ATUALIZA_AUTORIZACAO_CONV executada com sucesso")

            return {
                'procedure_guia_status': 'SUCESSO',
                'procedure_guia_mensagem': 'Dados da guia atualizados com sucesso'
            }

        except Exception as e:
            logger.error(f"Erro ao executar RPA_ATUALIZA_AUTORIZACAO_CONV: {e}")
            if self._connection:
                self._connection.rollback()
            return {
                'procedure_guia_status': 'ERRO',
                'procedure_guia_mensagem': str(e)
            }

    def atualizar_estagio_autorizacao(
        self,
        nr_sequencia: int,
        status_autorizacao: str
    ) -> dict:
        """
        Atualiza estágio da autorização no Tasy.

        PROCEDURE: TASY.ATUALIZAR_AUTORIZACAO_CONVENIO

        Parâmetros:
        - NR_SEQUENCIA_P: Número sequencial (BPM_AUTORIZACOES_V.NR_SEQUENCIA)
        - NM_USUARIO_P: Usuário ('automacaotasy')
        - NR_SEQ_ESTAGIO_P: Estágio (2=Aprovado, 6/29=Análise, 7=Negado)
        - IE_CONTA_PARTICULAR_P: 'N'
        - IE_CONTA_CONVENIO_P: 'N'
        - IE_COMMIT_P: 'S'
        """
        call_sql = """
            BEGIN
                TASY.ATUALIZAR_AUTORIZACAO_CONVENIO(
                    :p_nr_sequencia,
                    :p_nm_usuario,
                    :p_nr_seq_estagio,
                    :p_ie_conta_particular,
                    :p_ie_conta_convenio,
                    :p_ie_commit
                );
            END;
        """

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Mapeia status do RPA para estágio do Tasy
            nr_seq_estagio = obter_estagio_por_status(status_autorizacao)

            logger.info(f"Chamando ATUALIZAR_AUTORIZACAO_CONVENIO - "
                       f"nr_sequencia: {nr_sequencia}, "
                       f"status_autorizacao: {status_autorizacao}, "
                       f"nr_seq_estagio: {nr_seq_estagio}")

            cursor.execute(call_sql, {
                'p_nr_sequencia': nr_sequencia,
                'p_nm_usuario': 'automacaotasy',
                'p_nr_seq_estagio': nr_seq_estagio,
                'p_ie_conta_particular': 'N',
                'p_ie_conta_convenio': 'N',
                'p_ie_commit': 'S'
            })

            conn.commit()

            logger.info(f"Procedure ATUALIZAR_AUTORIZACAO_CONVENIO executada com sucesso")

            return {
                'procedure_estagio_status': 'SUCESSO',
                'procedure_estagio_mensagem': f'Estágio atualizado para {nr_seq_estagio}',
                'nr_seq_estagio': nr_seq_estagio
            }

        except Exception as e:
            logger.error(f"Erro ao executar ATUALIZAR_AUTORIZACAO_CONVENIO: {e}")
            if self._connection:
                self._connection.rollback()
            return {
                'procedure_estagio_status': 'ERRO',
                'procedure_estagio_mensagem': str(e),
                'nr_seq_estagio': None
            }

    def close(self):
        """Fecha conexão com o banco."""
        if self._connection:
            self._connection.close()
            self._connection = None


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_atualizar_autorizacao(task: ExternalTask) -> TaskResult:
    """
    Handler para atualizar autorização no Tasy.

    Executa duas procedures:
    1. RPA_ATUALIZA_AUTORIZACAO_CONV - Atualiza dados da guia
    2. ATUALIZAR_AUTORIZACAO_CONVENIO - Atualiza estágio

    INPUT (do processo Camunda):
    - nr_sequencia: Número sequencial da autorização no Tasy (obrigatório)
    - nr_guia_requisicao: Número da guia retornado pelo RPA
    - status_autorizacao: Status retornado pelo RPA (Autorizado, Negado, Analise)

    OUTPUT (para o processo Camunda):
    - oracle_status: SUCESSO ou ERRO
    - oracle_mensagem: Descrição do resultado
    - nr_seq_estagio: Estágio atribuído no Tasy
    """
    logger.info(f"Processando task (Atualizar Autorização): {task.get_task_id()}")

    variables = task.get_variables()

    # Parâmetros obrigatórios
    nr_sequencia = variables.get('nr_sequencia')

    # Parâmetros do RPA
    nr_guia_requisicao = variables.get('nr_guia_requisicao')
    status_autorizacao = variables.get('status_autorizacao')

    logger.info(f"Dados recebidos - nr_sequencia: {nr_sequencia}, "
               f"nr_guia_requisicao: {nr_guia_requisicao}, "
               f"status_autorizacao: {status_autorizacao}")

    # Validação
    if not nr_sequencia:
        logger.error("nr_sequencia não informado")
        return TaskResult.failure(
            task,
            error_message="nr_sequencia é obrigatório",
            error_details="O parâmetro nr_sequencia deve ser informado ao iniciar o processo",
            retries=0,
            retry_timeout=5000
        )

    # Converte para int se necessário
    try:
        nr_sequencia = int(nr_sequencia)
    except (ValueError, TypeError):
        logger.error(f"nr_sequencia inválido: {nr_sequencia}")
        return TaskResult.failure(
            task,
            error_message=f"nr_sequencia inválido: {nr_sequencia}",
            error_details="O parâmetro nr_sequencia deve ser um número inteiro",
            retries=0,
            retry_timeout=5000
        )

    repository = OracleAutorizacaoRepository(OracleConfig())

    try:
        resultado_final = {
            'oracle_status': 'SUCESSO',
            'oracle_mensagem': '',
            'nr_seq_estagio': None
        }
        mensagens = []

        # 1. Atualiza dados da guia (se nr_guia_requisicao foi informado)
        if nr_guia_requisicao:
            resultado_guia = repository.atualizar_autorizacao_guia(
                nr_sequencia=nr_sequencia,
                nr_guia_requisicao=str(nr_guia_requisicao)
            )

            if resultado_guia['procedure_guia_status'] == 'ERRO':
                resultado_final['oracle_status'] = 'ERRO'
                mensagens.append(f"Guia: {resultado_guia['procedure_guia_mensagem']}")
            else:
                mensagens.append("Guia atualizada")
        else:
            mensagens.append("Guia não informada (ignorado)")

        # 2. Atualiza estágio da autorização
        if status_autorizacao:
            resultado_estagio = repository.atualizar_estagio_autorizacao(
                nr_sequencia=nr_sequencia,
                status_autorizacao=status_autorizacao
            )

            if resultado_estagio['procedure_estagio_status'] == 'ERRO':
                resultado_final['oracle_status'] = 'ERRO'
                mensagens.append(f"Estágio: {resultado_estagio['procedure_estagio_mensagem']}")
            else:
                resultado_final['nr_seq_estagio'] = resultado_estagio['nr_seq_estagio']
                mensagens.append(f"Estágio: {resultado_estagio['nr_seq_estagio']}")
        else:
            mensagens.append("Status não informado (ignorado)")

        resultado_final['oracle_mensagem'] = ' | '.join(mensagens)

        logger.info(f"Resultado final: {resultado_final}")

        return TaskResult.success(task, resultado_final)

    except Exception as e:
        logger.error(f"Erro ao atualizar autorização: {e}")
        return TaskResult.success(
            task,
            {
                'oracle_status': 'ERRO',
                'oracle_mensagem': str(e),
                'nr_seq_estagio': None
            }
        )

    finally:
        repository.close()


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia worker para atualizar autorizações no Oracle/Tasy."""
    config = CamundaConfig()

    logger.info(f"Iniciando worker: {config.worker_id}")
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: oracle-registrar-autorizacao")

    worker_config = {
        "maxTasks": config.max_tasks,
        "lockDuration": config.lock_duration,
        "asyncResponseTimeout": 10000,
        "retries": 3,
        "retryTimeout": 5000,
        "sleepSeconds": config.sleep_seconds
    }

    worker = ExternalTaskWorker(
        worker_id=config.worker_id,
        base_url=config.base_url,
        config=worker_config
    )

    worker.subscribe(
        topic_names="oracle-registrar-autorizacao",
        action=handle_atualizar_autorizacao
    )


if __name__ == "__main__":
    main()
