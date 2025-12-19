"""
External Task Worker: Autorizacao Inteligente
==============================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Processa autorizacoes automaticamente
- Integra com Oracle/Tasy para validacao
- Executa IBM RPA quando necessario
- Retorna status da autorizacao

O BPMN ja definiu que esta tarefa deve ser executada.
O codigo NAO decide caminhos do processo.

Topic: autorizacao-inteligente
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from dotenv import load_dotenv
from camunda.external_task.external_task import ExternalTask, TaskResult
from camunda.external_task.external_task_worker import ExternalTaskWorker

# Carrega variaveis de ambiente
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACAO
# =============================================================================
@dataclass
class AutorizacaoConfig:
    """Configuracoes do servico de autorizacao."""
    api_url: str = os.getenv("API_AUTORIZACAO_URL", "https://bus.austaclinicas.com.br/api/autorizacao")
    api_timeout: int = int(os.getenv("API_BUS_TIMEOUT_SECONDS", "30"))

    # Oracle
    oracle_host: str = os.getenv("ORACLE_HOST", "10.100.0.9")
    oracle_port: int = int(os.getenv("ORACLE_PORT", "1521"))
    oracle_service: str = os.getenv("ORACLE_SERVICE_NAME", "dbhausta")
    oracle_user: str = os.getenv("ORACLE_USER", "tasy")
    oracle_password: str = os.getenv("ORACLE_PASSWORD", "")

    # IBM RPA
    rpa_api_url: str = os.getenv("IBM_RPA_API_URL", "https://br1api.rpa.ibm.com")
    rpa_workspace_id: str = os.getenv("IBM_RPA_WORKSPACE_ID", "")
    rpa_process_id: str = os.getenv("IBM_RPA_PROCESS_AUTORIZACAO", "")


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-autorizacao-inteligente"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION_EXTENDED", "600000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE DE AUTORIZACAO
# =============================================================================
class AutorizacaoClient:
    """
    Cliente para processamento de autorizacoes.
    NAO contem logica de negocio - apenas operacoes tecnicas.

    Meta: 85% das autorizacoes processadas automaticamente em < 5 minutos.
    """

    def __init__(self, config: AutorizacaoConfig):
        self.config = config
        self._session = None
        self._oracle_conn = None

    def _get_session(self):
        """Obtem sessao HTTP."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        return self._session

    def validar_elegibilidade(self, beneficiario_id: str, procedimento_codigo: str) -> dict:
        """
        Valida elegibilidade do beneficiario para o procedimento.

        Args:
            beneficiario_id: ID do beneficiario
            procedimento_codigo: Codigo do procedimento

        Returns:
            Resultado da validacao
        """
        logger.info(f"Validando elegibilidade: beneficiario={beneficiario_id}, proc={procedimento_codigo}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/elegibilidade"
            payload = {
                "beneficiario_id": beneficiario_id,
                "procedimento_codigo": procedimento_codigo
            }

            response = session.post(url, json=payload, timeout=self.config.api_timeout)

            if response.status_code == 200:
                dados = response.json()
                return {
                    "elegivel": dados.get("elegivel", False),
                    "carencia_cumprida": dados.get("carencia_cumprida", True),
                    "cobertura_valida": dados.get("cobertura_valida", True),
                    "limite_disponivel": dados.get("limite_disponivel", True),
                    "motivo_negativa": dados.get("motivo_negativa"),
                    "tipo_autorizacao": dados.get("tipo_autorizacao", "AUTOMATICA")
                }
            else:
                return {
                    "elegivel": False,
                    "motivo_negativa": f"Erro na validacao: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro na validacao de elegibilidade: {e}")
            return {
                "elegivel": False,
                "motivo_negativa": str(e)
            }

    def processar_autorizacao_automatica(
        self,
        beneficiario_id: str,
        procedimento_codigo: str,
        medico_crm: str,
        convenio_codigo: str,
        dados_adicionais: dict = None
    ) -> dict:
        """
        Processa autorizacao automatica.

        Args:
            beneficiario_id: ID do beneficiario
            procedimento_codigo: Codigo do procedimento
            medico_crm: CRM do medico solicitante
            convenio_codigo: Codigo do convenio
            dados_adicionais: Dados extras para autorizacao

        Returns:
            Resultado da autorizacao
        """
        logger.info(f"Processando autorizacao automatica para: {beneficiario_id}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/processar"
            payload = {
                "beneficiario_id": beneficiario_id,
                "procedimento_codigo": procedimento_codigo,
                "medico_crm": medico_crm,
                "convenio_codigo": convenio_codigo,
                "tipo_processamento": "AUTOMATICO",
                "dados_adicionais": dados_adicionais or {}
            }

            response = session.post(url, json=payload, timeout=self.config.api_timeout)

            if response.status_code in [200, 201]:
                dados = response.json()
                return {
                    "status": dados.get("status", "PROCESSANDO"),
                    "numero_autorizacao": dados.get("numero_autorizacao"),
                    "guia_id": dados.get("guia_id"),
                    "data_autorizacao": dados.get("data_autorizacao"),
                    "validade": dados.get("validade"),
                    "observacoes": dados.get("observacoes")
                }
            else:
                return {
                    "status": "ERRO",
                    "mensagem_erro": f"Erro no processamento: {response.status_code}",
                    "detalhes": response.text
                }

        except Exception as e:
            logger.error(f"Erro no processamento automatico: {e}")
            return {
                "status": "ERRO",
                "mensagem_erro": str(e)
            }

    def registrar_autorizacao_oracle(
        self,
        guia_id: str,
        numero_autorizacao: str,
        status: str,
        observacoes: str = None
    ) -> dict:
        """
        Registra autorizacao no Oracle/Tasy.

        Args:
            guia_id: ID da guia
            numero_autorizacao: Numero da autorizacao
            status: Status da autorizacao
            observacoes: Observacoes adicionais

        Returns:
            Resultado do registro
        """
        logger.info(f"Registrando autorizacao no Tasy: guia={guia_id}")

        try:
            import oracledb

            # Inicializa modo thick se necessario
            oracle_client_path = os.getenv("ORACLE_CLIENT_PATH")
            if oracle_client_path:
                try:
                    oracledb.init_oracle_client(lib_dir=oracle_client_path)
                except Exception:
                    pass  # Ja inicializado

            dsn = oracledb.makedsn(
                self.config.oracle_host,
                self.config.oracle_port,
                service_name=self.config.oracle_service
            )

            with oracledb.connect(
                user=self.config.oracle_user,
                password=self.config.oracle_password,
                dsn=dsn
            ) as connection:
                with connection.cursor() as cursor:
                    # Chama procedure de atualizacao
                    cursor.callproc("TASY.RPA_ATUALIZA_AUTORIZACAO_CONV", [
                        guia_id,
                        numero_autorizacao,
                        status,
                        observacoes
                    ])
                    connection.commit()

            return {
                "registrado": True,
                "data_registro": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erro ao registrar no Oracle: {e}")
            return {
                "registrado": False,
                "erro": str(e)
            }

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_autorizacao_inteligente(task: ExternalTask) -> TaskResult:
    """
    Handler para autorizacao inteligente.

    INPUT (do processo Camunda):
    - beneficiario_id: String
    - procedimento_codigo: String
    - medico_crm: String
    - convenio_codigo: String
    - tipo_procedimento: String (CONSULTA, EXAME, CIRURGIA, etc)
    - dados_clinicos: JSON (opcional)

    OUTPUT (para o processo Camunda):
    - autorizacao_status: String (APROVADA, NEGADA, PENDENTE_AUDITORIA)
    - numero_autorizacao: String
    - guia_id: String
    - autorizacao_tipo: String (AUTOMATICA, MANUAL)
    - autorizacao_data: String
    - autorizacao_validade: String
    - motivo_negativa: String (se negada)
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    # 1. Recebe variaveis do processo
    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    procedimento_codigo = variables.get('procedimento_codigo')
    medico_crm = variables.get('medico_crm')
    convenio_codigo = variables.get('convenio_codigo')
    tipo_procedimento = variables.get('tipo_procedimento', 'CONSULTA')
    dados_clinicos = variables.get('dados_clinicos', {})

    logger.info(f"Autorizacao para: benef={beneficiario_id}, proc={procedimento_codigo}, conv={convenio_codigo}")

    # 2. Validacao tecnica
    if not all([beneficiario_id, procedimento_codigo, convenio_codigo]):
        return TaskResult.failure(
            task,
            error_message="Parametros obrigatorios faltando",
            error_details="beneficiario_id, procedimento_codigo e convenio_codigo sao obrigatorios",
            retries=0,
            retry_timeout=5000
        )

    # 3. Processa autorizacao
    config = AutorizacaoConfig()
    client = AutorizacaoClient(config)

    try:
        # Valida elegibilidade
        elegibilidade = client.validar_elegibilidade(beneficiario_id, procedimento_codigo)

        if not elegibilidade.get("elegivel"):
            return TaskResult.success(task, {
                'autorizacao_status': 'NEGADA',
                'autorizacao_tipo': 'AUTOMATICA',
                'motivo_negativa': elegibilidade.get('motivo_negativa'),
                'autorizacao_data': datetime.now().isoformat()
            })

        # Processa autorizacao
        resultado = client.processar_autorizacao_automatica(
            beneficiario_id=beneficiario_id,
            procedimento_codigo=procedimento_codigo,
            medico_crm=medico_crm,
            convenio_codigo=convenio_codigo,
            dados_adicionais={
                "tipo_procedimento": tipo_procedimento,
                "dados_clinicos": dados_clinicos
            }
        )

        if resultado.get("status") == "ERRO":
            return TaskResult.success(task, {
                'autorizacao_status': 'PENDENTE_AUDITORIA',
                'autorizacao_tipo': 'AUTOMATICA',
                'autorizacao_erro': resultado.get('mensagem_erro'),
                'autorizacao_data': datetime.now().isoformat()
            })

        # Registra no Oracle/Tasy
        if resultado.get("numero_autorizacao"):
            client.registrar_autorizacao_oracle(
                guia_id=resultado.get("guia_id"),
                numero_autorizacao=resultado.get("numero_autorizacao"),
                status="AUTORIZADO",
                observacoes="Autorizacao processada automaticamente"
            )

        # 4. Retorna resultado
        return TaskResult.success(task, {
            'autorizacao_status': 'APROVADA',
            'numero_autorizacao': resultado.get('numero_autorizacao'),
            'guia_id': resultado.get('guia_id'),
            'autorizacao_tipo': 'AUTOMATICA',
            'autorizacao_data': resultado.get('data_autorizacao', datetime.now().isoformat()),
            'autorizacao_validade': resultado.get('validade'),
            'autorizacao_observacoes': resultado.get('observacoes')
        })

    except Exception as e:
        logger.error(f"Erro tecnico na autorizacao: {e}")
        return TaskResult.success(task, {
            'autorizacao_status': 'PENDENTE_AUDITORIA',
            'autorizacao_tipo': 'AUTOMATICA',
            'autorizacao_erro': str(e),
            'autorizacao_data': datetime.now().isoformat()
        })

    finally:
        client.close()


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia o worker."""
    config = CamundaConfig()

    logger.info("=" * 60)
    logger.info("WORKER: Autorizacao Inteligente")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: autorizacao-inteligente")
    logger.info("Meta: 85% das autorizacoes em < 5 minutos")
    logger.info("=" * 60)

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
        topic_names="autorizacao-inteligente",
        action=handle_autorizacao_inteligente
    )


if __name__ == "__main__":
    main()
