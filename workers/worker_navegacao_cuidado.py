"""
External Task Worker: Navegacao do Cuidado
==========================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Atribui navegador ao beneficiario
- Direciona para rede preferencial
- Orquestra jornada de cuidado
- Coordena etapas do tratamento

O BPMN ja definiu que esta tarefa deve ser executada.
O codigo NAO decide caminhos do processo.

Topics:
- navegacao-atribuir-navegador
- navegacao-rede-preferencial
- navegacao-orquestrar-jornada
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

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
class NavegacaoConfig:
    """Configuracoes do servico de navegacao."""
    api_url: str = os.getenv("API_BUS_URL", "https://bus.austaclinicas.com.br/api")
    api_prestador_url: str = os.getenv("API_PRESTADOR_URL", "https://bus.austaclinicas.com.br/api/prestador")
    api_timeout: int = int(os.getenv("API_BUS_TIMEOUT_SECONDS", "30"))
    rede_preferencial_enabled: bool = os.getenv("REDE_PREFERENCIAL_ENABLED", "true").lower() == "true"
    rede_preferencial_bonus: int = int(os.getenv("REDE_PREFERENCIAL_BONUS_SCORE", "20"))


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-navegacao-cuidado"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION", "30000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE DE NAVEGACAO
# =============================================================================
class NavegacaoClient:
    """
    Cliente para servicos de navegacao do cuidado.
    NAO contem logica de negocio - apenas operacoes tecnicas.
    """

    def __init__(self, config: NavegacaoConfig):
        self.config = config
        self._session = None

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

    def buscar_navegador_disponivel(self, nivel_risco: str, especialidade: str = None) -> dict:
        """
        Busca navegador disponivel para o caso.

        Args:
            nivel_risco: Nivel de risco do beneficiario
            especialidade: Especialidade necessaria (opcional)

        Returns:
            Dados do navegador
        """
        logger.info(f"Buscando navegador para nivel de risco: {nivel_risco}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/navegador/disponivel"
            params = {
                "nivel_risco": nivel_risco,
                "especialidade": especialidade
            }

            response = session.get(url, params=params, timeout=self.config.api_timeout)

            if response.status_code == 200:
                dados = response.json()
                return {
                    "encontrado": True,
                    "navegador_id": dados.get("id"),
                    "navegador_nome": dados.get("nome"),
                    "navegador_telefone": dados.get("telefone"),
                    "navegador_email": dados.get("email"),
                    "carga_atual": dados.get("carga_atual", 0),
                    "especialidades": dados.get("especialidades", [])
                }
            else:
                return {
                    "encontrado": False,
                    "motivo": "Nenhum navegador disponivel"
                }

        except Exception as e:
            logger.error(f"Erro ao buscar navegador: {e}")
            return {
                "encontrado": False,
                "motivo": str(e)
            }

    def atribuir_navegador(self, beneficiario_id: str, navegador_id: str, caso_detalhes: dict) -> dict:
        """
        Atribui navegador ao beneficiario.

        Args:
            beneficiario_id: ID do beneficiario
            navegador_id: ID do navegador
            caso_detalhes: Detalhes do caso

        Returns:
            Resultado da atribuicao
        """
        logger.info(f"Atribuindo navegador {navegador_id} ao beneficiario {beneficiario_id}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/navegador/atribuir"
            payload = {
                "beneficiario_id": beneficiario_id,
                "navegador_id": navegador_id,
                "caso": caso_detalhes
            }

            response = session.post(url, json=payload, timeout=self.config.api_timeout)

            if response.status_code in [200, 201]:
                dados = response.json()
                return {
                    "atribuido": True,
                    "caso_id": dados.get("caso_id"),
                    "data_atribuicao": dados.get("data_atribuicao", datetime.now().isoformat())
                }
            else:
                return {
                    "atribuido": False,
                    "erro": f"Erro na atribuicao: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao atribuir navegador: {e}")
            return {
                "atribuido": False,
                "erro": str(e)
            }

    def buscar_rede_preferencial(
        self,
        especialidade: str,
        localizacao: dict,
        convenio_codigo: str
    ) -> List[dict]:
        """
        Busca prestadores na rede preferencial (Tier A).

        Args:
            especialidade: Especialidade medica
            localizacao: Localizacao do beneficiario
            convenio_codigo: Codigo do convenio

        Returns:
            Lista de prestadores ordenados por score
        """
        logger.info(f"Buscando rede preferencial: {especialidade}")

        if not self.config.rede_preferencial_enabled:
            logger.info("Rede preferencial desabilitada")
            return []

        session = self._get_session()

        try:
            url = f"{self.config.api_prestador_url}/preferencial"
            params = {
                "especialidade": especialidade,
                "latitude": localizacao.get("latitude"),
                "longitude": localizacao.get("longitude"),
                "convenio": convenio_codigo,
                "tier": "A"
            }

            response = session.get(url, params=params, timeout=self.config.api_timeout)

            if response.status_code == 200:
                prestadores = response.json().get("prestadores", [])

                # Adiciona bonus de score para rede preferencial
                for p in prestadores:
                    p["score"] = p.get("score", 0) + self.config.rede_preferencial_bonus

                # Ordena por score
                prestadores.sort(key=lambda x: x.get("score", 0), reverse=True)

                return prestadores
            else:
                return []

        except Exception as e:
            logger.error(f"Erro ao buscar rede preferencial: {e}")
            return []

    def criar_jornada_cuidado(
        self,
        beneficiario_id: str,
        caso_id: str,
        etapas: List[dict]
    ) -> dict:
        """
        Cria jornada de cuidado com etapas definidas.

        Args:
            beneficiario_id: ID do beneficiario
            caso_id: ID do caso
            etapas: Lista de etapas da jornada

        Returns:
            Jornada criada
        """
        logger.info(f"Criando jornada de cuidado para caso: {caso_id}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/jornada/criar"
            payload = {
                "beneficiario_id": beneficiario_id,
                "caso_id": caso_id,
                "etapas": etapas
            }

            response = session.post(url, json=payload, timeout=self.config.api_timeout)

            if response.status_code in [200, 201]:
                dados = response.json()
                return {
                    "criada": True,
                    "jornada_id": dados.get("jornada_id"),
                    "etapas_criadas": len(etapas),
                    "proxima_etapa": etapas[0] if etapas else None
                }
            else:
                return {
                    "criada": False,
                    "erro": f"Erro ao criar jornada: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao criar jornada: {e}")
            return {
                "criada": False,
                "erro": str(e)
            }

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# HANDLERS DOS EXTERNAL TASKS
# =============================================================================
def handle_atribuir_navegador(task: ExternalTask) -> TaskResult:
    """
    Handler para atribuir navegador ao beneficiario.

    INPUT:
    - beneficiario_id: String
    - beneficiario_nome: String
    - nivel_risco: String (ALTO, COMPLEXO)
    - especialidade_necessaria: String (opcional)
    - caso_resumo: String

    OUTPUT:
    - navegador_atribuido: Boolean
    - navegador_id: String
    - navegador_nome: String
    - navegador_telefone: String
    - caso_id: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    beneficiario_nome = variables.get('beneficiario_nome')
    nivel_risco = variables.get('nivel_risco', 'ALTO')
    especialidade = variables.get('especialidade_necessaria')
    caso_resumo = variables.get('caso_resumo', '')

    if not beneficiario_id:
        return TaskResult.failure(
            task,
            error_message="beneficiario_id e obrigatorio",
            error_details="O ID do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = NavegacaoConfig()
    client = NavegacaoClient(config)

    try:
        # Busca navegador disponivel
        navegador = client.buscar_navegador_disponivel(nivel_risco, especialidade)

        if not navegador.get("encontrado"):
            return TaskResult.success(task, {
                'navegador_atribuido': False,
                'navegador_motivo': navegador.get('motivo')
            })

        # Atribui navegador
        caso_detalhes = {
            "beneficiario_nome": beneficiario_nome,
            "nivel_risco": nivel_risco,
            "resumo": caso_resumo,
            "data_abertura": datetime.now().isoformat()
        }

        resultado = client.atribuir_navegador(
            beneficiario_id=beneficiario_id,
            navegador_id=navegador.get("navegador_id"),
            caso_detalhes=caso_detalhes
        )

        if resultado.get("atribuido"):
            return TaskResult.success(task, {
                'navegador_atribuido': True,
                'navegador_id': navegador.get('navegador_id'),
                'navegador_nome': navegador.get('navegador_nome'),
                'navegador_telefone': navegador.get('navegador_telefone'),
                'navegador_email': navegador.get('navegador_email'),
                'caso_id': resultado.get('caso_id'),
                'data_atribuicao': resultado.get('data_atribuicao')
            })
        else:
            return TaskResult.success(task, {
                'navegador_atribuido': False,
                'navegador_erro': resultado.get('erro')
            })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'navegador_atribuido': False,
            'navegador_erro': str(e)
        })

    finally:
        client.close()


def handle_rede_preferencial(task: ExternalTask) -> TaskResult:
    """
    Handler para direcionar para rede preferencial.

    INPUT:
    - especialidade: String
    - beneficiario_latitude: Float
    - beneficiario_longitude: Float
    - convenio_codigo: String

    OUTPUT:
    - rede_preferencial_encontrada: Boolean
    - prestadores: List[JSON]
    - prestador_recomendado: JSON
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    especialidade = variables.get('especialidade')
    latitude = variables.get('beneficiario_latitude')
    longitude = variables.get('beneficiario_longitude')
    convenio_codigo = variables.get('convenio_codigo')

    if not especialidade:
        return TaskResult.failure(
            task,
            error_message="especialidade e obrigatoria",
            error_details="A especialidade deve ser informada",
            retries=0,
            retry_timeout=5000
        )

    config = NavegacaoConfig()
    client = NavegacaoClient(config)

    try:
        localizacao = {
            "latitude": latitude,
            "longitude": longitude
        }

        prestadores = client.buscar_rede_preferencial(
            especialidade=especialidade,
            localizacao=localizacao,
            convenio_codigo=convenio_codigo
        )

        if prestadores:
            return TaskResult.success(task, {
                'rede_preferencial_encontrada': True,
                'prestadores': prestadores[:5],  # Top 5
                'prestador_recomendado': prestadores[0],
                'total_encontrados': len(prestadores)
            })
        else:
            return TaskResult.success(task, {
                'rede_preferencial_encontrada': False,
                'prestadores': [],
                'total_encontrados': 0
            })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'rede_preferencial_encontrada': False,
            'rede_erro': str(e)
        })

    finally:
        client.close()


def handle_orquestrar_jornada(task: ExternalTask) -> TaskResult:
    """
    Handler para orquestrar jornada de cuidado.

    INPUT:
    - beneficiario_id: String
    - caso_id: String
    - etapas_jornada: List[JSON]

    OUTPUT:
    - jornada_criada: Boolean
    - jornada_id: String
    - proxima_etapa: JSON
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    caso_id = variables.get('caso_id')
    etapas = variables.get('etapas_jornada', [])

    if not beneficiario_id or not caso_id:
        return TaskResult.failure(
            task,
            error_message="Parametros obrigatorios faltando",
            error_details="beneficiario_id e caso_id sao obrigatorios",
            retries=0,
            retry_timeout=5000
        )

    # Se nao houver etapas definidas, cria etapas padrao
    if not etapas:
        etapas = [
            {"ordem": 1, "tipo": "CONSULTA_INICIAL", "status": "PENDENTE"},
            {"ordem": 2, "tipo": "EXAMES", "status": "PENDENTE"},
            {"ordem": 3, "tipo": "RETORNO", "status": "PENDENTE"},
            {"ordem": 4, "tipo": "ACOMPANHAMENTO", "status": "PENDENTE"}
        ]

    config = NavegacaoConfig()
    client = NavegacaoClient(config)

    try:
        resultado = client.criar_jornada_cuidado(
            beneficiario_id=beneficiario_id,
            caso_id=caso_id,
            etapas=etapas
        )

        if resultado.get("criada"):
            return TaskResult.success(task, {
                'jornada_criada': True,
                'jornada_id': resultado.get('jornada_id'),
                'etapas_total': resultado.get('etapas_criadas'),
                'proxima_etapa': resultado.get('proxima_etapa'),
                'jornada_data_criacao': datetime.now().isoformat()
            })
        else:
            return TaskResult.success(task, {
                'jornada_criada': False,
                'jornada_erro': resultado.get('erro')
            })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'jornada_criada': False,
            'jornada_erro': str(e)
        })

    finally:
        client.close()


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia o worker com multiplos topics."""
    config = CamundaConfig()

    logger.info("=" * 60)
    logger.info("WORKER: Navegacao do Cuidado")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info("Topics:")
    logger.info("  - navegacao-atribuir-navegador")
    logger.info("  - navegacao-rede-preferencial")
    logger.info("  - navegacao-orquestrar-jornada")
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
        topic_names="navegacao-atribuir-navegador",
        action=handle_atribuir_navegador
    )

    worker.subscribe(
        topic_names="navegacao-rede-preferencial",
        action=handle_rede_preferencial
    )

    worker.subscribe(
        topic_names="navegacao-orquestrar-jornada",
        action=handle_orquestrar_jornada
    )


if __name__ == "__main__":
    main()
