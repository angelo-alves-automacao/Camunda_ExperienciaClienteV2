"""
External Task Worker: Follow-up e NPS
======================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Envia follow-up pos-atendimento
- Coleta NPS (Net Promoter Score)
- Analisa desfechos clinicos
- Atualiza modelos de ML

O BPMN ja definiu que esta tarefa deve ser executada.
O codigo NAO decide caminhos do processo.

Topics:
- followup-pos-atendimento
- followup-coletar-nps
- analytics-analisar-desfechos
- ml-atualizar-modelos
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
class FollowupConfig:
    """Configuracoes do servico de follow-up."""
    api_url: str = os.getenv("API_BUS_URL", "https://bus.austaclinicas.com.br/api")
    whatsapp_api_url: str = os.getenv("WHATSAPP_API_URL", "https://api.whatsapp.austa.com.br")
    whatsapp_token: str = os.getenv("WHATSAPP_API_TOKEN", "")
    template_nps: str = os.getenv("WHATSAPP_TEMPLATE_NPS", "pesquisa_nps")


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-followup-nps"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION", "30000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE DE FOLLOW-UP
# =============================================================================
class FollowupClient:
    """
    Cliente para servicos de follow-up e NPS.
    NAO contem logica de negocio - apenas operacoes tecnicas.
    """

    def __init__(self, config: FollowupConfig):
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

    def enviar_followup(
        self,
        beneficiario_id: str,
        telefone: str,
        tipo_atendimento: str,
        data_atendimento: str
    ) -> dict:
        """
        Envia mensagem de follow-up pos-atendimento.

        Args:
            beneficiario_id: ID do beneficiario
            telefone: Telefone do beneficiario
            tipo_atendimento: Tipo do atendimento realizado
            data_atendimento: Data do atendimento

        Returns:
            Resultado do envio
        """
        logger.info(f"Enviando follow-up para beneficiario: {beneficiario_id}")

        session = self._get_session()
        session.headers['Authorization'] = f'Bearer {self.config.whatsapp_token}'

        try:
            # Monta mensagem de follow-up
            mensagem = self._montar_mensagem_followup(tipo_atendimento, data_atendimento)

            payload = {
                "messaging_product": "whatsapp",
                "to": self._formatar_telefone(telefone),
                "type": "text",
                "text": {"body": mensagem}
            }

            response = session.post(
                f"{self.config.whatsapp_api_url}/messages",
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                return {
                    "enviado": True,
                    "message_id": response.json().get("messages", [{}])[0].get("id"),
                    "data_envio": datetime.now().isoformat()
                }
            else:
                return {
                    "enviado": False,
                    "erro": f"Erro no envio: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao enviar follow-up: {e}")
            return {
                "enviado": False,
                "erro": str(e)
            }

    def _montar_mensagem_followup(self, tipo_atendimento: str, data_atendimento: str) -> str:
        """Monta mensagem de follow-up personalizada."""
        mensagens = {
            "CONSULTA": "Ola! Como voce esta se sentindo apos sua consulta? Ficou alguma duvida?",
            "EXAME": "Ola! Seu exame foi realizado com sucesso. O resultado estara disponivel em breve.",
            "PROCEDIMENTO": "Ola! Esperamos que esteja se recuperando bem. Precisa de algum suporte?",
            "INTERNACAO": "Ola! Esperamos que sua recuperacao esteja indo bem. Nossa equipe esta a disposicao.",
            "AUTORIZACAO": "Ola! Sua solicitacao foi processada. Ficou alguma duvida sobre os proximos passos?"
        }

        return mensagens.get(tipo_atendimento, "Ola! Como podemos ajuda-lo hoje?")

    def enviar_pesquisa_nps(self, beneficiario_id: str, telefone: str, contexto: dict) -> dict:
        """
        Envia pesquisa NPS.

        Args:
            beneficiario_id: ID do beneficiario
            telefone: Telefone do beneficiario
            contexto: Contexto do atendimento

        Returns:
            Resultado do envio
        """
        logger.info(f"Enviando pesquisa NPS para beneficiario: {beneficiario_id}")

        session = self._get_session()
        session.headers['Authorization'] = f'Bearer {self.config.whatsapp_token}'

        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": self._formatar_telefone(telefone),
                "type": "template",
                "template": {
                    "name": self.config.template_nps,
                    "language": {"code": "pt_BR"},
                    "components": [{
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": contexto.get("tipo_atendimento", "atendimento")}
                        ]
                    }]
                }
            }

            response = session.post(
                f"{self.config.whatsapp_api_url}/messages",
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                return {
                    "enviado": True,
                    "pesquisa_id": f"NPS_{beneficiario_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "data_envio": datetime.now().isoformat()
                }
            else:
                return {
                    "enviado": False,
                    "erro": f"Erro no envio: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao enviar NPS: {e}")
            return {
                "enviado": False,
                "erro": str(e)
            }

    def registrar_resposta_nps(self, pesquisa_id: str, nota: int, comentario: str = None) -> dict:
        """
        Registra resposta da pesquisa NPS.

        Args:
            pesquisa_id: ID da pesquisa
            nota: Nota de 0 a 10
            comentario: Comentario do beneficiario

        Returns:
            Resultado do registro
        """
        logger.info(f"Registrando resposta NPS: {pesquisa_id}, nota={nota}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/nps/resposta"
            payload = {
                "pesquisa_id": pesquisa_id,
                "nota": nota,
                "comentario": comentario,
                "classificacao": self._classificar_nps(nota),
                "data_resposta": datetime.now().isoformat()
            }

            response = session.post(url, json=payload, timeout=30)

            if response.status_code in [200, 201]:
                return {
                    "registrado": True,
                    "classificacao": payload["classificacao"]
                }
            else:
                return {
                    "registrado": False,
                    "erro": f"Erro no registro: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao registrar NPS: {e}")
            return {
                "registrado": False,
                "erro": str(e)
            }

    def _classificar_nps(self, nota: int) -> str:
        """Classifica resposta NPS."""
        if nota >= 9:
            return "PROMOTOR"
        elif nota >= 7:
            return "NEUTRO"
        else:
            return "DETRATOR"

    def _formatar_telefone(self, telefone: str) -> str:
        """Formata telefone para formato internacional."""
        numeros = ''.join(filter(str.isdigit, telefone))
        if len(numeros) <= 11:
            numeros = f"55{numeros}"
        return numeros

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# CLIENTE DE ANALYTICS
# =============================================================================
class AnalyticsClient:
    """
    Cliente para analise de desfechos.
    NAO contem logica de negocio - apenas operacoes tecnicas.
    """

    def __init__(self, config: FollowupConfig):
        self.config = config
        self._session = None

    def _get_session(self):
        """Obtem sessao HTTP."""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def analisar_desfechos(self, beneficiario_id: str, periodo_dias: int = 30) -> dict:
        """
        Analisa desfechos clinicos do beneficiario.

        Args:
            beneficiario_id: ID do beneficiario
            periodo_dias: Periodo de analise em dias

        Returns:
            Analise de desfechos
        """
        logger.info(f"Analisando desfechos para: {beneficiario_id}")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/analytics/desfechos"
            params = {
                "beneficiario_id": beneficiario_id,
                "periodo_dias": periodo_dias
            }

            response = session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                dados = response.json()
                return {
                    "analisado": True,
                    "internacoes": dados.get("internacoes", 0),
                    "readmissoes": dados.get("readmissoes", 0),
                    "complicacoes": dados.get("complicacoes", 0),
                    "consultas_realizadas": dados.get("consultas_realizadas", 0),
                    "exames_realizados": dados.get("exames_realizados", 0),
                    "adesao_tratamento": dados.get("adesao_tratamento", 0),
                    "custo_periodo": dados.get("custo_periodo", 0),
                    "score_desfecho": dados.get("score_desfecho", 0)
                }
            else:
                return {
                    "analisado": False,
                    "erro": f"Erro na analise: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao analisar desfechos: {e}")
            return {
                "analisado": False,
                "erro": str(e)
            }

    def atualizar_modelo_ml(self, dados_treinamento: dict) -> dict:
        """
        Envia dados para atualizacao do modelo de ML.

        Args:
            dados_treinamento: Dados para retreinamento

        Returns:
            Resultado da atualizacao
        """
        logger.info("Enviando dados para atualizacao do modelo ML")

        session = self._get_session()

        try:
            url = f"{self.config.api_url}/ml/atualizar"
            payload = {
                "dados": dados_treinamento,
                "timestamp": datetime.now().isoformat()
            }

            response = session.post(url, json=payload, timeout=60)

            if response.status_code in [200, 201, 202]:
                return {
                    "atualizado": True,
                    "job_id": response.json().get("job_id"),
                    "data_atualizacao": datetime.now().isoformat()
                }
            else:
                return {
                    "atualizado": False,
                    "erro": f"Erro na atualizacao: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Erro ao atualizar modelo: {e}")
            return {
                "atualizado": False,
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
def handle_followup_pos_atendimento(task: ExternalTask) -> TaskResult:
    """
    Handler para enviar follow-up pos-atendimento.

    INPUT:
    - beneficiario_id: String
    - beneficiario_telefone: String
    - tipo_atendimento: String
    - data_atendimento: String

    OUTPUT:
    - followup_enviado: Boolean
    - followup_message_id: String
    - followup_data: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    telefone = variables.get('beneficiario_telefone')
    tipo_atendimento = variables.get('tipo_atendimento', 'CONSULTA')
    data_atendimento = variables.get('data_atendimento', datetime.now().isoformat())

    if not beneficiario_id or not telefone:
        return TaskResult.failure(
            task,
            error_message="Parametros obrigatorios faltando",
            error_details="beneficiario_id e beneficiario_telefone sao obrigatorios",
            retries=0,
            retry_timeout=5000
        )

    config = FollowupConfig()
    client = FollowupClient(config)

    try:
        resultado = client.enviar_followup(
            beneficiario_id=beneficiario_id,
            telefone=telefone,
            tipo_atendimento=tipo_atendimento,
            data_atendimento=data_atendimento
        )

        return TaskResult.success(task, {
            'followup_enviado': resultado.get('enviado', False),
            'followup_message_id': resultado.get('message_id', ''),
            'followup_data': resultado.get('data_envio', datetime.now().isoformat()),
            'followup_erro': resultado.get('erro')
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'followup_enviado': False,
            'followup_erro': str(e)
        })

    finally:
        client.close()


def handle_coletar_nps(task: ExternalTask) -> TaskResult:
    """
    Handler para coletar NPS.

    INPUT:
    - beneficiario_id: String
    - beneficiario_telefone: String
    - tipo_atendimento: String

    OUTPUT:
    - nps_enviado: Boolean
    - nps_pesquisa_id: String
    - nps_data_envio: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    telefone = variables.get('beneficiario_telefone')
    tipo_atendimento = variables.get('tipo_atendimento', 'ATENDIMENTO')

    if not beneficiario_id or not telefone:
        return TaskResult.failure(
            task,
            error_message="Parametros obrigatorios faltando",
            error_details="beneficiario_id e beneficiario_telefone sao obrigatorios",
            retries=0,
            retry_timeout=5000
        )

    config = FollowupConfig()
    client = FollowupClient(config)

    try:
        contexto = {"tipo_atendimento": tipo_atendimento}
        resultado = client.enviar_pesquisa_nps(
            beneficiario_id=beneficiario_id,
            telefone=telefone,
            contexto=contexto
        )

        return TaskResult.success(task, {
            'nps_enviado': resultado.get('enviado', False),
            'nps_pesquisa_id': resultado.get('pesquisa_id', ''),
            'nps_data_envio': resultado.get('data_envio', datetime.now().isoformat()),
            'nps_erro': resultado.get('erro')
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'nps_enviado': False,
            'nps_erro': str(e)
        })

    finally:
        client.close()


def handle_analisar_desfechos(task: ExternalTask) -> TaskResult:
    """
    Handler para analisar desfechos.

    INPUT:
    - beneficiario_id: String
    - periodo_dias: Integer (opcional, default 30)

    OUTPUT:
    - desfechos_analisados: Boolean
    - desfechos_internacoes: Integer
    - desfechos_readmissoes: Integer
    - desfechos_score: Float
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    periodo_dias = variables.get('periodo_dias', 30)

    if not beneficiario_id:
        return TaskResult.failure(
            task,
            error_message="beneficiario_id e obrigatorio",
            error_details="O ID do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = FollowupConfig()
    client = AnalyticsClient(config)

    try:
        resultado = client.analisar_desfechos(beneficiario_id, periodo_dias)

        return TaskResult.success(task, {
            'desfechos_analisados': resultado.get('analisado', False),
            'desfechos_internacoes': resultado.get('internacoes', 0),
            'desfechos_readmissoes': resultado.get('readmissoes', 0),
            'desfechos_complicacoes': resultado.get('complicacoes', 0),
            'desfechos_adesao': resultado.get('adesao_tratamento', 0),
            'desfechos_score': resultado.get('score_desfecho', 0),
            'desfechos_custo': resultado.get('custo_periodo', 0),
            'desfechos_data_analise': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'desfechos_analisados': False,
            'desfechos_erro': str(e)
        })

    finally:
        client.close()


def handle_atualizar_modelos(task: ExternalTask) -> TaskResult:
    """
    Handler para atualizar modelos de ML.

    INPUT:
    - dados_feedback: JSON (dados coletados para retreinamento)

    OUTPUT:
    - ml_atualizado: Boolean
    - ml_job_id: String
    - ml_data_atualizacao: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    dados_feedback = variables.get('dados_feedback', {})

    config = FollowupConfig()
    client = AnalyticsClient(config)

    try:
        resultado = client.atualizar_modelo_ml(dados_feedback)

        return TaskResult.success(task, {
            'ml_atualizado': resultado.get('atualizado', False),
            'ml_job_id': resultado.get('job_id', ''),
            'ml_data_atualizacao': resultado.get('data_atualizacao', datetime.now().isoformat()),
            'ml_erro': resultado.get('erro')
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'ml_atualizado': False,
            'ml_erro': str(e)
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
    logger.info("WORKER: Follow-up e NPS")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info("Topics:")
    logger.info("  - followup-pos-atendimento")
    logger.info("  - followup-coletar-nps")
    logger.info("  - analytics-analisar-desfechos")
    logger.info("  - ml-atualizar-modelos")
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
        topic_names="followup-pos-atendimento",
        action=handle_followup_pos_atendimento
    )

    worker.subscribe(
        topic_names="followup-coletar-nps",
        action=handle_coletar_nps
    )

    worker.subscribe(
        topic_names="analytics-analisar-desfechos",
        action=handle_analisar_desfechos
    )

    worker.subscribe(
        topic_names="ml-atualizar-modelos",
        action=handle_atualizar_modelos
    )


if __name__ == "__main__":
    main()
