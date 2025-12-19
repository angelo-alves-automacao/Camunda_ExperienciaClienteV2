"""
External Task Worker: Oracle - Notificação WhatsApp via Tasy
=============================================================

Responsabilidade TÉCNICA (não contém regras de negócio):
- Inserir registro na tabela TASY.AUSTA_ENVIOS_WHATSAPP
- O trigger do banco dispara automaticamente o envio do WhatsApp

A tabela AUSTA_ENVIOS_WHATSAPP possui trigger que processa envios automaticamente.

O BPMN já definiu que esta tarefa deve ser executada.
O código NÃO decide caminhos do processo.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import oracledb

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / '.env')

# Inicializa Oracle Client (modo thick) para suportar autenticação legada
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
    worker_id: str = "oracle-notificacao-worker"
    max_tasks: int = 1
    lock_duration: int = 30000
    sleep_seconds: int = 5


# =============================================================================
# MAPEAMENTO DE STATUS PARA MODELO DE MENSAGEM
# =============================================================================
# CD_MODELO determina qual template de mensagem WhatsApp será enviado
STATUS_PARA_MODELO = {
    "Autorizado": 27,     # Aprovado
    "AUTORIZADO": 27,
    "Aprovado": 27,
    "APROVADO": 27,
    "Negado": 3,          # Negado
    "NEGADO": 3,
    "Recusado": 3,
    "RECUSADO": 3,
}

# Default para outros status (Analise, Auditoria, etc.)
MODELO_DEFAULT = 27


def obter_modelo_por_status(status_autorizacao: str) -> int:
    """
    Converte status_autorizacao para CD_MODELO da tabela AUSTA_ENVIOS_WHATSAPP.

    Mapeamento:
    - Autorizado/Aprovado -> 27 (template aprovado)
    - Negado/Recusado -> 3 (template negado)

    Default: 27 se status desconhecido ou vazio
    """
    if not status_autorizacao:
        return MODELO_DEFAULT

    return STATUS_PARA_MODELO.get(status_autorizacao.strip(), MODELO_DEFAULT)


# =============================================================================
# REPOSITÓRIO ORACLE - NOTIFICAÇÃO WHATSAPP
# =============================================================================
class OracleNotificacaoRepository:
    """
    Repositório para inserir notificações WhatsApp no Oracle/Tasy.
    A tabela AUSTA_ENVIOS_WHATSAPP possui trigger que dispara o envio.
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

    def inserir_notificacao_whatsapp(
        self,
        nr_sequencia: int,
        status_autorizacao: str,
        nr_telefone: str = "5517981872857"
    ) -> dict:
        """
        Insere registro na tabela AUSTA_ENVIOS_WHATSAPP.
        O trigger do banco dispara automaticamente o envio.

        Parâmetros:
        - nr_sequencia: Número sequencial da autorização
        - status_autorizacao: Status para determinar o modelo (Autorizado/Negado)
        - nr_telefone: Telefone do destinatário (default para teste)

        Campos inseridos:
        - CD_MODELO: 27 (aprovado) ou 3 (negado)
        - DT_CRIACAO: SYSDATE
        - DT_ENVIO: SYSDATE
        - DS_PARAMETROS: NULL
        - CD_STATUS: 0
        - DS_MENSAGEM_ERRO: NULL
        - CD_STATUS_ENVIO: 1
        - NR_TELEFONE: telefone do destinatário
        - NR_SEQ_AUTORIZACAO: nr_sequencia
        - DATA_AUTORIZACAO: SYSDATE
        - DATA_CONSULTA: SYSDATE
        """
        insert_sql = """
            INSERT INTO TASY.AUSTA_ENVIOS_WHATSAPP (
                CD_MODELO,
                DT_CRIACAO,
                DT_ENVIO,
                DS_PARAMETROS,
                CD_STATUS,
                DS_MENSAGEM_ERRO,
                CD_STATUS_ENVIO,
                NR_TELEFONE,
                NR_SEQ_AUTORIZACAO,
                DATA_AUTORIZACAO,
                DATA_CONSULTA
            ) VALUES (
                :cd_modelo,
                SYSDATE,
                SYSDATE,
                NULL,
                0,
                NULL,
                1,
                :nr_telefone,
                :nr_seq_autorizacao,
                SYSDATE,
                SYSDATE
            )
        """

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Determina o modelo de mensagem baseado no status
            cd_modelo = obter_modelo_por_status(status_autorizacao)

            logger.info(f"Inserindo notificação WhatsApp - "
                       f"nr_sequencia: {nr_sequencia}, "
                       f"status: {status_autorizacao}, "
                       f"cd_modelo: {cd_modelo}, "
                       f"telefone: {nr_telefone}")

            cursor.execute(insert_sql, {
                'cd_modelo': cd_modelo,
                'nr_telefone': nr_telefone,
                'nr_seq_autorizacao': nr_sequencia
            })

            conn.commit()

            logger.info(f"Notificação WhatsApp inserida com sucesso - trigger disparará envio")

            return {
                'notificacao_status': 'SUCESSO',
                'notificacao_mensagem': f'Notificação inserida - modelo {cd_modelo}',
                'cd_modelo': cd_modelo
            }

        except Exception as e:
            logger.error(f"Erro ao inserir notificação WhatsApp: {e}")
            if self._connection:
                self._connection.rollback()
            return {
                'notificacao_status': 'ERRO',
                'notificacao_mensagem': str(e),
                'cd_modelo': None
            }

    def close(self):
        """Fecha conexão com o banco."""
        if self._connection:
            self._connection.close()
            self._connection = None


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_notificar_medico(task: ExternalTask) -> TaskResult:
    """
    Handler para notificar médico via WhatsApp.

    Insere registro na tabela AUSTA_ENVIOS_WHATSAPP.
    O trigger do banco Oracle dispara automaticamente o envio da mensagem.

    INPUT (do processo Camunda):
    - nr_sequencia: Número sequencial da autorização no Tasy (obrigatório)
    - status_autorizacao: Status da autorização (Autorizado, Negado, etc.)
    - nr_telefone: Telefone do médico (opcional, usa default se não informado)

    OUTPUT (para o processo Camunda):
    - notificacao_status: SUCESSO ou ERRO
    - notificacao_mensagem: Descrição do resultado
    - cd_modelo: Código do modelo de mensagem usado
    """
    logger.info(f"Processando task (Notificar Médico): {task.get_task_id()}")

    variables = task.get_variables()

    # Parâmetros
    nr_sequencia = variables.get('nr_sequencia')
    status_autorizacao = variables.get('status_autorizacao')
    nr_telefone = variables.get('nr_telefone', '5517981872857')  # Default para teste

    logger.info(f"Dados recebidos - nr_sequencia: {nr_sequencia}, "
               f"status_autorizacao: {status_autorizacao}, "
               f"nr_telefone: {nr_telefone}")

    # Validação
    if not nr_sequencia:
        logger.error("nr_sequencia não informado")
        return TaskResult.failure(
            task,
            error_message="nr_sequencia é obrigatório",
            error_details="O parâmetro nr_sequencia deve ser informado",
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

    repository = OracleNotificacaoRepository(OracleConfig())

    try:
        # Insere notificação (trigger dispara envio)
        resultado = repository.inserir_notificacao_whatsapp(
            nr_sequencia=nr_sequencia,
            status_autorizacao=status_autorizacao,
            nr_telefone=str(nr_telefone)
        )

        logger.info(f"Resultado notificação: {resultado}")

        return TaskResult.success(task, resultado)

    except Exception as e:
        logger.error(f"Erro ao notificar médico: {e}")
        return TaskResult.success(
            task,
            {
                'notificacao_status': 'ERRO',
                'notificacao_mensagem': str(e),
                'cd_modelo': None
            }
        )

    finally:
        repository.close()


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia worker para notificações WhatsApp via Oracle/Tasy."""
    config = CamundaConfig()

    logger.info(f"Iniciando worker: {config.worker_id}")
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: oracle-notificacao-medico")

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
        topic_names="oracle-notificacao-medico",
        action=handle_notificar_medico
    )


if __name__ == "__main__":
    main()
