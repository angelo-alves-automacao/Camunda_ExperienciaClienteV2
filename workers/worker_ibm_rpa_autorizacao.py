"""
External Task Worker: IBM RPA - Autorização Cirúrgica
======================================================

Responsabilidade TÉCNICA (não contém regras de negócio):
- Disparar processo IBM RPA via API (Process Management)
- Retornar status técnico ao processo Camunda

O BPMN já definiu que esta tarefa deve ser executada.
O DMN já decidiu que este convênio usa automação RPA.
O código NÃO decide caminhos do processo.
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
import requests

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / '.env')
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
class IBMRPAConfig:
    """Configuração do IBM RPA (deve vir de variáveis de ambiente)."""
    api_url: str = os.getenv("IBM_RPA_API_URL", "https://br1api.rpa.ibm.com")
    workspace_id: str = os.getenv("IBM_RPA_WORKSPACE_ID", "")
    tenant_id: str = os.getenv("IBM_RPA_TENANT_ID", "")
    username: str = os.getenv("IBM_RPA_USERNAME", "")
    password: str = os.getenv("IBM_RPA_PASSWORD", "")
    process_id: str = os.getenv("IBM_RPA_PROCESS_ID", "")
    timeout_seconds: int = int(os.getenv("IBM_RPA_TIMEOUT_SECONDS", "300"))
    poll_interval_seconds: int = int(os.getenv("IBM_RPA_POLL_INTERVAL_SECONDS", "10"))


@dataclass
class CamundaConfig:
    base_url: str = os.getenv("CAMUNDA_URL", "https://camundahml.austa.com.br/engine-rest")
    worker_id: str = "ibm-rpa-worker-001"
    max_tasks: int = 1
    lock_duration: int = 600000  # 10 minutos (RPA pode demorar)
    sleep_seconds: int = 5


class RPAStatus(Enum):
    """Status de execução do RPA."""
    SUCESSO = "SUCESSO"
    ERRO = "ERRO"
    TIMEOUT = "TIMEOUT"
    PENDENTE = "PENDENTE"


# =============================================================================
# CLIENTE IBM RPA (Process Management API)
# =============================================================================
class IBMRPAClient:
    """
    Cliente para API do IBM RPA - Process Management.
    Executa apenas operações técnicas de integração.
    NÃO contém lógica de negócio.

    Usa autenticação OAuth com username/password conforme documentação IBM RPA.
    Endpoint: POST /v2.0/workspace/{workspaceId}/process/{processId}/instance
    """

    def __init__(self, config: IBMRPAConfig):
        self.config = config
        self._access_token: Optional[str] = None

    def _obter_token(self) -> str:
        """
        Obtém access token via OAuth usando username/password.

        POST /v1.0/token
        Headers: tenantId, Content-Type: application/x-www-form-urlencoded
        Body: grant_type=password&username=...&password=...&culture=en-US
        """
        if self._access_token:
            return self._access_token

        token_url = f"{self.config.api_url}/v1.0/token"

        headers = {
            'tenantId': self.config.tenant_id,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'IBM-RPA-Worker/1.0',
            'Accept': '*/*'
        }

        payload = (
            f"grant_type=password"
            f"&username={requests.utils.quote(self.config.username)}"
            f"&password={requests.utils.quote(self.config.password)}"
            f"&culture=en-US"
        )

        logger.info("Obtendo token IBM RPA...")

        response = requests.post(token_url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        self._access_token = data.get('access_token')

        logger.info("Token IBM RPA obtido com sucesso")
        return self._access_token

    def _get_headers(self) -> dict:
        """Retorna headers com token de autenticação."""
        token = self._obter_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'IBM-RPA-Worker/1.0',
            'Accept': 'application/json'
        }

    def iniciar_processo(self, process_id: str, payload: dict) -> str:
        """
        Inicia uma instância de processo no IBM RPA.

        POST /v2.0/workspace/{workspaceId}/process/{processId}/instance

        INPUT TÉCNICO:
        - process_id: UUID do processo no IBM RPA
        - payload: Dicionário com variáveis de entrada

        OUTPUT TÉCNICO:
        - instance_id: UUID da instância criada
        """
        endpoint = (
            f"{self.config.api_url}/v2.0/workspace/{self.config.workspace_id}"
            f"/process/{process_id}/instance"
        )

        # Payload conforme documentação IBM RPA
        request_body = {
            "payload": payload
        }

        try:
            headers = self._get_headers()
            logger.info(f"Iniciando processo IBM RPA: {process_id}")
            logger.info(f"Endpoint: {endpoint}")

            response = requests.post(endpoint, headers=headers, json=request_body, timeout=30)
            response.raise_for_status()

            data = response.json()
            instance_id = data.get('id')

            logger.info(f"Processo iniciado - Instance ID: {instance_id}")
            return instance_id

        except requests.RequestException as e:
            logger.error(f"Erro ao iniciar processo: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def consultar_status_instancia(self, process_id: str, instance_id: str) -> dict:
        """
        Consulta o status de uma instância de processo no IBM RPA.

        GET /v2.0/workspace/{workspaceId}/process/{processId}/instance/{instanceId}

        Retorna dict com informações da instância incluindo status.
        """
        endpoint = (
            f"{self.config.api_url}/v2.0/workspace/{self.config.workspace_id}"
            f"/process/{process_id}/instance/{instance_id}"
        )

        headers = self._get_headers()
        response = requests.get(endpoint, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()

    def aguardar_conclusao(self, process_id: str, instance_id: str) -> Tuple[str, str, Optional[dict]]:
        """
        Aguarda a conclusão do processo IBM RPA com polling.

        Retorna:
        - status: 'SUCESSO', 'ERRO' ou 'TIMEOUT'
        - mensagem: Descrição do resultado
        - output: Dados de saída do processo (se houver)
        """
        tempo_inicio = time.time()
        tempo_maximo = self.config.timeout_seconds

        logger.info(f"Aguardando conclusão do processo (timeout: {tempo_maximo}s)...")

        while True:
            tempo_decorrido = time.time() - tempo_inicio

            if tempo_decorrido >= tempo_maximo:
                logger.warning(f"Timeout aguardando processo: {instance_id}")
                return RPAStatus.TIMEOUT.value, f"Timeout após {tempo_maximo}s", None

            try:
                data = self.consultar_status_instancia(process_id, instance_id)
                status = data.get('status', '').upper()

                logger.info(f"Status atual: {status} (tempo: {tempo_decorrido:.0f}s)")

                # Status possíveis do IBM RPA Process:
                # - NEW: Recém criado
                # - QUEUED: Na fila
                # - PROCESSING: Em execução
                # - RUNNING: Em execução
                # - DONE: Finalizado com sucesso
                # - COMPLETED: Finalizado com sucesso
                # - FAILED: Falhou
                # - CANCELED: Cancelado
                if status in ('DONE', 'COMPLETED'):
                    # IBM RPA retorna:
                    # - outputs: dict com variáveis de saída (ex: status_autorizacao, nr_guia_requisicao)
                    # - variables: lista de dicts com variáveis de entrada/saída
                    outputs = data.get('outputs', {}) or data.get('output', {})
                    variables = data.get('variables', [])
                    logger.info(f"Processo concluído! Outputs: {outputs}, Variables: {variables}")
                    return RPAStatus.SUCESSO.value, "Processo concluído com sucesso", {"outputs": outputs, "variables": variables}

                elif status in ('FAILED', 'CANCELED', 'ERROR'):
                    error_msg = data.get('errorMessage') or data.get('error') or 'Erro desconhecido'
                    return RPAStatus.ERRO.value, f"Processo falhou: {error_msg}", data

                elif status in ('NEW', 'QUEUED', 'PROCESSING', 'RUNNING', 'PENDING'):
                    # Ainda em execução, aguarda próximo poll
                    time.sleep(self.config.poll_interval_seconds)
                else:
                    # Status desconhecido
                    logger.warning(f"Status desconhecido: {status}")
                    time.sleep(self.config.poll_interval_seconds)

            except requests.RequestException as e:
                logger.error(f"Erro ao consultar status: {e}")
                time.sleep(self.config.poll_interval_seconds)


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_executar_rpa(task: ExternalTask) -> TaskResult:
    """
    Handler para o External Task de execução RPA.

    RESPONSABILIDADE:
    - Receber variáveis do processo Camunda (já decididas pelo BPMN/DMN)
    - Executar integração técnica com IBM RPA via Process Management API
    - Retornar resultados técnicos ao processo

    NÃO FAZ:
    - Decisões de negócio
    - Escolha de qual convênio processar (já decidido pelo DMN)
    - Controle de fluxo

    INPUT (do processo Camunda):
    - paciente_nome: String
    - convenio_codigo: Integer
    - procedimento_codigo: Integer
    - medico_crm: Integer
    - guia_solicitacao: Integer

    OUTPUT (para o processo Camunda):
    - rpa_status: String (SUCESSO, ERRO, TIMEOUT)
    - rpa_instance_id: String (UUID da instância no IBM RPA)
    - rpa_mensagem: String (mensagem descritiva)
    - rpa_data_execucao: String (ISO datetime)
    - numero_autorizacao: String (número da autorização obtida)
    - status_autorizacao: String (Autorizado, Negado, Analise)
    - nr_guia_requisicao: String (número da guia de requisição)
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    # Recebe variáveis do processo Camunda
    variables = task.get_variables()

    paciente_nome = variables.get('paciente_nome', '')
    convenio_codigo = variables.get('convenio_codigo')
    procedimento_codigo = variables.get('procedimento_codigo')
    medico_crm = variables.get('medico_crm')
    guia_solicitacao = variables.get('guia_solicitacao')

    logger.info(f"Executando RPA para convênio: {convenio_codigo}")

    # Carrega configuração
    config = IBMRPAConfig()

    if not config.process_id:
        logger.error("IBM_RPA_PROCESS_ID não configurado no .env")
        return TaskResult.failure(
            task,
            error_message="Processo IBM RPA não configurado",
            error_details="A variável IBM_RPA_PROCESS_ID não está definida no .env",
            retries=0,
            retry_timeout=5000
        )

    # Monta payload para o processo IBM RPA
    rpa_payload = {
        "paciente_nome": paciente_nome or "",
        "convenio_codigo": int(convenio_codigo) if convenio_codigo else 0,
        "procedimento_codigo": int(procedimento_codigo) if procedimento_codigo else 0,
        "medico_crm": int(medico_crm) if medico_crm else 0,
        "guia_solicitacao": int(guia_solicitacao) if guia_solicitacao else 0
    }

    # Execução técnica
    client = IBMRPAClient(config)

    try:
        # 1. Inicia o processo IBM RPA
        instance_id = client.iniciar_processo(
            process_id=config.process_id,
            payload=rpa_payload
        )

        # 2. Aguarda conclusão com polling
        rpa_status, rpa_mensagem, rpa_output = client.aguardar_conclusao(
            process_id=config.process_id,
            instance_id=instance_id
        )

        # 3. Extrai variáveis de saída do script RPA
        # IMPORTANTE: rpa_status indica se o SCRIPT executou (SUCESSO/ERRO/TIMEOUT)
        # As variáveis abaixo são OUTPUTS do script que indicam o resultado da autorização
        numero_autorizacao = None
        status_autorizacao = None  # Autorizado, Negado, Analise (resultado da autorização)
        nr_guia_requisicao = None

        if rpa_output and isinstance(rpa_output, dict):
            outputs = rpa_output.get('outputs', {})
            variables = rpa_output.get('variables', [])

            # Log do output completo para debug
            logger.info(f"RPA Output completo: {rpa_output}")

            # Extrai status_autorizacao (variável de saída do script)
            # Valores esperados: Autorizado, Negado, Analise
            status_autorizacao = (
                outputs.get('status_autorizacao') or
                outputs.get('statusAutorizacao')
            )

            # Extrai nr_guia_requisicao (variável de saída do script)
            # Pode vir como número (ex: 95687.0), converte para string inteira
            nr_guia_raw = (
                outputs.get('nr_guia_requisicao') or
                outputs.get('nrGuiaRequisicao') or
                outputs.get('guia_requisicao')
            )
            if nr_guia_raw is not None:
                # Converte para inteiro se for float, depois para string
                if isinstance(nr_guia_raw, float):
                    nr_guia_requisicao = str(int(nr_guia_raw))
                else:
                    nr_guia_requisicao = str(nr_guia_raw)

            # Extrai numero_autorizacao (variável de saída do script, se existir)
            numero_autorizacao = (
                outputs.get('numero_autorizacao') or
                outputs.get('numeroAutorizacao') or
                outputs.get('nr_autorizacao')
            )

            # Tenta também buscar nas variables (lista de dicts com 'name' e 'value')
            if isinstance(variables, list):
                for var in variables:
                    var_name = var.get('name', '')
                    var_value = var.get('value')
                    if var_name in ('numero_autorizacao', 'numeroAutorizacao', 'nr_autorizacao') and not numero_autorizacao:
                        numero_autorizacao = var_value
                    elif var_name in ('status_autorizacao', 'statusAutorizacao') and not status_autorizacao:
                        status_autorizacao = var_value
                    elif var_name in ('nr_guia_requisicao', 'nrGuiaRequisicao', 'guia_requisicao') and not nr_guia_requisicao:
                        # Converte para inteiro se for float
                        if isinstance(var_value, float):
                            nr_guia_requisicao = str(int(var_value))
                        elif var_value is not None:
                            nr_guia_requisicao = str(var_value)

        logger.info(f"RPA finalizado - Execução: {rpa_status}, "
                    f"Status Autorização: {status_autorizacao}, "
                    f"Nr Autorização: {numero_autorizacao}, "
                    f"Nr Guia Requisição: {nr_guia_requisicao}")

        # 4. Retorna resultado para o Camunda
        # O BPMN verifica rpa_status == 'SUCESSO' ou rpa_status == 'ERRO'
        return TaskResult.success(
            task,
            {
                "rpa_status": rpa_status,
                "rpa_instance_id": instance_id,
                "rpa_mensagem": rpa_mensagem,
                "rpa_data_execucao": datetime.now().isoformat(),
                "numero_autorizacao": numero_autorizacao,
                "status_autorizacao": status_autorizacao,
                "nr_guia_requisicao": nr_guia_requisicao
            }
        )

    except Exception as e:
        logger.error(f"Erro técnico na execução RPA: {e}")
        # Retorna ERRO como rpa_status (script não executou)
        # status_autorizacao fica None pois não houve execução do script
        return TaskResult.success(
            task,
            {
                "rpa_status": RPAStatus.ERRO.value,
                "rpa_instance_id": None,
                "rpa_mensagem": f"Erro técnico: {e}",
                "rpa_data_execucao": datetime.now().isoformat(),
                "numero_autorizacao": None,
                "status_autorizacao": None,
                "nr_guia_requisicao": None
            }
        )


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicializa o External Task Worker para IBM RPA."""
    config = CamundaConfig()

    logger.info(f"Iniciando worker: {config.worker_id}")
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: ibm-rpa-autorizacao")

    worker_config = {
        "maxTasks": config.max_tasks,
        "lockDuration": config.lock_duration,
        "asyncResponseTimeout": 30000,
        "retries": 2,
        "retryTimeout": 30000,
        "sleepSeconds": config.sleep_seconds
    }

    worker = ExternalTaskWorker(
        worker_id=config.worker_id,
        base_url=config.base_url,
        config=worker_config
    )

    worker.subscribe(
        topic_names="ibm-rpa-autorizacao",
        action=handle_executar_rpa
    )


if __name__ == "__main__":
    main()
