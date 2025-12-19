"""
External Task Worker: API - Consulta Paciente
==============================================

Responsabilidade TÉCNICA (não contém regras de negócio):
- Chamar API de consulta de paciente
- Retornar dados técnicos ao processo

O BPMN já definiu que esta tarefa deve ser executada.
O código NÃO decide caminhos do processo.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
import requests
from camunda.external_task.external_task import ExternalTask, TaskResult
from camunda.external_task.external_task_worker import ExternalTaskWorker

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / '.env')

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
class APIConfig:
    """Configuração da API de consulta de paciente."""
    base_url: str = os.getenv("API_PACIENTE_URL", "https://bus.austaclinicas.com.br/api/autorizacao/cirurgia")
    timeout_seconds: int = int(os.getenv("API_TIMEOUT_SECONDS", "30"))


@dataclass
class CamundaConfig:
    base_url: str = os.getenv("CAMUNDA_URL", "https://camundahml.austa.com.br/engine-rest")
    worker_id: str = "api-consulta-paciente-worker"
    max_tasks: int = 1
    lock_duration: int = 30000  # 30 segundos
    sleep_seconds: int = 5


# =============================================================================
# CLIENTE API PACIENTE
# =============================================================================
class PacienteAPIClient:
    """
    Cliente para API de consulta de paciente.
    Executa apenas operações técnicas de integração.
    NÃO contém lógica de negócio.
    """

    def __init__(self, config: APIConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def consultar_por_cpf(self, cpf: str) -> Optional[dict]:
        """
        Consulta paciente por CPF na API.

        INPUT TÉCNICO:
        - cpf: String com CPF do paciente

        OUTPUT TÉCNICO:
        - dict com dados do paciente ou None

        Resposta esperada da API:
        {
            "success": true,
            "data": [{
                "CD_PESSOA_FISICA": "131766",
                "NR_CPF": "22939549869",
                "NM_PESSOA_FISICA": "Nome do Paciente",
                "DT_NASCIMENTO": "1988-01-26 00:00:00",
                "QT_IDADE": "37",
                "QT_IDADE_MES": "10",
                "IE_SEXO": null,
                "DESC_SEXO": null,
                "TELEFONE": "551732213000"
            }]
        }
        """
        endpoint = f"{self.config.base_url}/paciente"

        try:
            response = self.session.get(
                endpoint,
                params={'cpf': cpf},
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()

            data = response.json()

            if data.get('success') and data.get('data'):
                paciente = data['data'][0]  # Pega o primeiro resultado
                return {
                    'paciente_id': paciente.get('CD_PESSOA_FISICA'),
                    'paciente_nome': paciente.get('NM_PESSOA_FISICA', '').strip(),
                    'cpf': paciente.get('NR_CPF'),
                    'data_nascimento': paciente.get('DT_NASCIMENTO'),
                    'idade': paciente.get('QT_IDADE'),
                    'sexo': paciente.get('DESC_SEXO'),
                    'telefone': paciente.get('TELEFONE')
                }

            return None

        except requests.RequestException as e:
            logger.error(f"Erro ao consultar API de paciente: {e}")
            raise


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_consulta_paciente(task: ExternalTask) -> TaskResult:
    """
    Handler para o External Task de consulta de paciente.

    RESPONSABILIDADE:
    - Receber variáveis do processo (cpf_paciente)
    - Executar consulta técnica na API
    - Retornar resultados técnicos ao processo

    NÃO FAZ:
    - Decisões de negócio
    - Validações de elegibilidade
    - Controle de fluxo

    INPUT (do processo BPMN):
    - cpf_paciente: CPF do paciente
    - convenio_codigo: Código do convênio (informado na solicitação)

    OUTPUT (para o processo BPMN):
    - paciente_encontrado: boolean
    - paciente_id: ID do paciente no Tasy
    - paciente_nome: Nome completo
    - convenio_codigo: Código do convênio (repassado)
    - plano_ativo: boolean (assumido true se encontrou)
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    # Recebe variáveis do processo (já definidas pelo BPMN)
    variables = task.get_variables()
    cpf_paciente = variables.get('cpf_paciente')
    convenio_codigo = variables.get('convenio_codigo')  # Vem da solicitação

    logger.info(f"Consultando paciente - CPF: {cpf_paciente}")

    # Execução técnica
    client = PacienteAPIClient(APIConfig())

    try:
        paciente = client.consultar_por_cpf(cpf_paciente)

        # Retorna resultados técnicos ao processo
        # O BPMN decidirá o que fazer com esses dados
        if paciente:
            logger.info(f"Paciente encontrado: {paciente['paciente_nome']}")
            return TaskResult.success(
                task,
                {
                    "paciente_encontrado": True,
                    "paciente_id": paciente['paciente_id'],
                    "paciente_nome": paciente['paciente_nome'],
                    "convenio_codigo": convenio_codigo,  # Repassa o que veio da solicitação
                    "convenio_nome": convenio_codigo,    # Pode ser ajustado se tiver lookup
                    "plano_ativo": True,                 # Assume ativo se encontrou
                    "paciente_telefone": paciente.get('telefone'),
                    "consulta_timestamp": datetime.now().isoformat()
                }
            )
        else:
            logger.warning(f"Paciente não encontrado para CPF: {cpf_paciente}")
            return TaskResult.success(
                task,
                {
                    "paciente_encontrado": False,
                    "paciente_id": None,
                    "paciente_nome": None,
                    "convenio_codigo": convenio_codigo,
                    "convenio_nome": None,
                    "plano_ativo": False,
                    "consulta_timestamp": datetime.now().isoformat()
                }
            )

    except Exception as e:
        logger.error(f"Erro técnico na consulta: {e}")
        # Retorna erro técnico - o BPMN tratará via boundary event
        return TaskResult.failure(
            task,
            error_message=str(e),
            error_details=f"Erro ao consultar API de paciente: {e}",
            retries=0,
            retry_timeout=5000
        )


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """
    Inicializa o External Task Worker.
    """
    config = CamundaConfig()

    logger.info(f"Iniciando worker: {config.worker_id}")
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: oracle-consulta-paciente")

    # Configuração do worker
    worker_config = {
        "maxTasks": config.max_tasks,
        "lockDuration": config.lock_duration,
        "asyncResponseTimeout": 10000,
        "retries": 3,
        "retryTimeout": 5000,
        "sleepSeconds": config.sleep_seconds
    }

    # Cria e inicia o worker
    worker = ExternalTaskWorker(
        worker_id=config.worker_id,
        base_url=config.base_url,
        config=worker_config
    )

    # Subscreve no tópico (mantém o mesmo nome para compatibilidade com BPMN)
    worker.subscribe(
        topic_names="oracle-consulta-paciente",
        action=handle_consulta_paciente
    )


if __name__ == "__main__":
    main()
