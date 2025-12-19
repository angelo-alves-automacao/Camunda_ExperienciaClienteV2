"""
External Task Worker: WhatsApp - Comunicacao Proativa
=====================================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Envia mensagens via WhatsApp Business API
- Processa templates de mensagem
- Retorna status do envio

O BPMN ja definiu que esta tarefa deve ser executada.
O codigo NAO decide caminhos do processo.

Topics:
- whatsapp-enviar-boas-vindas
- whatsapp-comunicacao-proativa
- whatsapp-comunicar-tempo-real
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
class WhatsAppConfig:
    """Configuracoes do WhatsApp Business API."""
    api_url: str = os.getenv("WHATSAPP_API_URL", "https://api.whatsapp.austa.com.br")
    api_token: str = os.getenv("WHATSAPP_API_TOKEN", "")
    phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    # Templates
    template_boas_vindas: str = os.getenv("WHATSAPP_TEMPLATE_BOAS_VINDAS", "boas_vindas_beneficiario")
    template_screening: str = os.getenv("WHATSAPP_TEMPLATE_SCREENING", "screening_saude")
    template_lembrete: str = os.getenv("WHATSAPP_TEMPLATE_LEMBRETE_CONSULTA", "lembrete_consulta")
    template_resultado: str = os.getenv("WHATSAPP_TEMPLATE_RESULTADO_EXAME", "resultado_exame_disponivel")
    template_autorizacao: str = os.getenv("WHATSAPP_TEMPLATE_AUTORIZACAO", "status_autorizacao")
    template_nps: str = os.getenv("WHATSAPP_TEMPLATE_NPS", "pesquisa_nps")


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-whatsapp-comunicacao"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION", "30000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE WHATSAPP
# =============================================================================
class WhatsAppClient:
    """
    Cliente para WhatsApp Business API.
    NAO contem logica de negocio - apenas operacoes tecnicas.
    """

    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self._session = None

    def _get_session(self):
        """Obtem sessao HTTP reutilizavel."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'Authorization': f'Bearer {self.config.api_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        return self._session

    def enviar_template(
        self,
        telefone: str,
        template_name: str,
        parametros: Dict[str, str],
        language: str = "pt_BR"
    ) -> dict:
        """
        Envia mensagem usando template pre-aprovado.

        Args:
            telefone: Numero do telefone com DDI
            template_name: Nome do template aprovado
            parametros: Parametros para o template
            language: Codigo do idioma

        Returns:
            Resultado do envio
        """
        logger.info(f"Enviando template '{template_name}' para {telefone}")

        session = self._get_session()

        # Formata telefone
        telefone_formatado = self._formatar_telefone(telefone)

        # Monta payload
        payload = {
            "messaging_product": "whatsapp",
            "to": telefone_formatado,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language
                },
                "components": self._montar_componentes(parametros)
            }
        }

        try:
            url = f"{self.config.api_url}/{self.config.phone_number_id}/messages"
            response = session.post(url, json=payload, timeout=30)

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": "ENVIADO",
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "telefone": telefone_formatado,
                    "template": template_name,
                    "data_envio": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "ERRO",
                    "codigo_erro": response.status_code,
                    "mensagem_erro": response.text,
                    "telefone": telefone_formatado,
                    "template": template_name
                }

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {
                "status": "ERRO",
                "mensagem_erro": str(e),
                "telefone": telefone_formatado,
                "template": template_name
            }

    def enviar_mensagem_texto(self, telefone: str, texto: str) -> dict:
        """
        Envia mensagem de texto simples.

        Args:
            telefone: Numero do telefone
            texto: Texto da mensagem

        Returns:
            Resultado do envio
        """
        logger.info(f"Enviando mensagem de texto para {telefone}")

        session = self._get_session()
        telefone_formatado = self._formatar_telefone(telefone)

        payload = {
            "messaging_product": "whatsapp",
            "to": telefone_formatado,
            "type": "text",
            "text": {
                "body": texto
            }
        }

        try:
            url = f"{self.config.api_url}/{self.config.phone_number_id}/messages"
            response = session.post(url, json=payload, timeout=30)

            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": "ENVIADO",
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "telefone": telefone_formatado,
                    "data_envio": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "ERRO",
                    "codigo_erro": response.status_code,
                    "mensagem_erro": response.text,
                    "telefone": telefone_formatado
                }

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {
                "status": "ERRO",
                "mensagem_erro": str(e),
                "telefone": telefone_formatado
            }

    def _formatar_telefone(self, telefone: str) -> str:
        """Formata telefone para formato internacional."""
        # Remove caracteres nao numericos
        numeros = ''.join(filter(str.isdigit, telefone))

        # Adiciona DDI Brasil se nao tiver
        if len(numeros) == 11:  # DDD + numero
            numeros = f"55{numeros}"
        elif len(numeros) == 10:  # DDD + numero antigo
            numeros = f"55{numeros}"

        return numeros

    def _montar_componentes(self, parametros: Dict[str, str]) -> List[dict]:
        """Monta componentes do template com parametros."""
        if not parametros:
            return []

        # Converte parametros para formato de componentes
        params_list = []
        for key, value in parametros.items():
            params_list.append({
                "type": "text",
                "text": str(value)
            })

        return [{
            "type": "body",
            "parameters": params_list
        }]

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# HANDLERS DOS EXTERNAL TASKS
# =============================================================================
def handle_enviar_boas_vindas(task: ExternalTask) -> TaskResult:
    """
    Handler para enviar mensagem de boas-vindas.

    INPUT:
    - beneficiario_nome: String
    - beneficiario_telefone: String

    OUTPUT:
    - whatsapp_status: String
    - whatsapp_message_id: String
    - whatsapp_data_envio: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    nome = variables.get('beneficiario_nome', 'Beneficiario')
    telefone = variables.get('beneficiario_telefone')

    if not telefone:
        return TaskResult.failure(
            task,
            error_message="beneficiario_telefone e obrigatorio",
            error_details="O telefone do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = WhatsAppConfig()
    client = WhatsAppClient(config)

    try:
        resultado = client.enviar_template(
            telefone=telefone,
            template_name=config.template_boas_vindas,
            parametros={"nome": nome}
        )

        return TaskResult.success(task, {
            'whatsapp_status': resultado.get('status'),
            'whatsapp_message_id': resultado.get('message_id', ''),
            'whatsapp_data_envio': resultado.get('data_envio', datetime.now().isoformat())
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'whatsapp_status': 'ERRO',
            'whatsapp_mensagem_erro': str(e)
        })

    finally:
        client.close()


def handle_comunicacao_proativa(task: ExternalTask) -> TaskResult:
    """
    Handler para enviar comunicacao proativa baseada em gatilhos.

    INPUT:
    - beneficiario_nome: String
    - beneficiario_telefone: String
    - tipo_gatilho: String (EXAME_VENCENDO, MEDICAMENTO_ACABANDO, CONSULTA_PENDENTE, etc)
    - dados_gatilho: JSON (dados especificos do gatilho)

    OUTPUT:
    - whatsapp_status: String
    - whatsapp_message_id: String
    - tipo_comunicacao: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    nome = variables.get('beneficiario_nome', 'Beneficiario')
    telefone = variables.get('beneficiario_telefone')
    tipo_gatilho = variables.get('tipo_gatilho', 'GERAL')
    dados_gatilho = variables.get('dados_gatilho', {})

    if not telefone:
        return TaskResult.failure(
            task,
            error_message="beneficiario_telefone e obrigatorio",
            error_details="O telefone do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = WhatsAppConfig()
    client = WhatsAppClient(config)

    # Mapeia tipo de gatilho para template
    template_map = {
        'EXAME_VENCENDO': config.template_lembrete,
        'MEDICAMENTO_ACABANDO': config.template_lembrete,
        'CONSULTA_PENDENTE': config.template_lembrete,
        'RESULTADO_DISPONIVEL': config.template_resultado,
        'AUTORIZACAO_ATUALIZADA': config.template_autorizacao,
    }

    template = template_map.get(tipo_gatilho, config.template_lembrete)

    try:
        parametros = {
            "nome": nome,
            **dados_gatilho
        }

        resultado = client.enviar_template(
            telefone=telefone,
            template_name=template,
            parametros=parametros
        )

        return TaskResult.success(task, {
            'whatsapp_status': resultado.get('status'),
            'whatsapp_message_id': resultado.get('message_id', ''),
            'tipo_comunicacao': tipo_gatilho,
            'whatsapp_data_envio': resultado.get('data_envio', datetime.now().isoformat())
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'whatsapp_status': 'ERRO',
            'whatsapp_mensagem_erro': str(e)
        })

    finally:
        client.close()


def handle_comunicar_tempo_real(task: ExternalTask) -> TaskResult:
    """
    Handler para comunicacao em tempo real sobre status do atendimento.

    INPUT:
    - beneficiario_nome: String
    - beneficiario_telefone: String
    - mensagem_status: String
    - etapa_atual: String

    OUTPUT:
    - whatsapp_status: String
    - whatsapp_message_id: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    nome = variables.get('beneficiario_nome', 'Beneficiario')
    telefone = variables.get('beneficiario_telefone')
    mensagem = variables.get('mensagem_status', '')
    etapa = variables.get('etapa_atual', '')

    if not telefone:
        return TaskResult.failure(
            task,
            error_message="beneficiario_telefone e obrigatorio",
            error_details="O telefone do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = WhatsAppConfig()
    client = WhatsAppClient(config)

    try:
        # Monta mensagem personalizada
        texto = f"Ola {nome}! {mensagem}"
        if etapa:
            texto += f"\n\nEtapa atual: {etapa}"

        resultado = client.enviar_mensagem_texto(telefone, texto)

        return TaskResult.success(task, {
            'whatsapp_status': resultado.get('status'),
            'whatsapp_message_id': resultado.get('message_id', ''),
            'whatsapp_data_envio': resultado.get('data_envio', datetime.now().isoformat())
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'whatsapp_status': 'ERRO',
            'whatsapp_mensagem_erro': str(e)
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
    logger.info("WORKER: WhatsApp - Comunicacao")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info("Topics:")
    logger.info("  - whatsapp-enviar-boas-vindas")
    logger.info("  - whatsapp-comunicacao-proativa")
    logger.info("  - whatsapp-comunicar-tempo-real")
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

    # Subscreve em multiplos topics
    worker.subscribe(
        topic_names="whatsapp-enviar-boas-vindas",
        action=handle_enviar_boas_vindas
    )

    worker.subscribe(
        topic_names="whatsapp-comunicacao-proativa",
        action=handle_comunicacao_proativa
    )

    worker.subscribe(
        topic_names="whatsapp-comunicar-tempo-real",
        action=handle_comunicar_tempo_real
    )


if __name__ == "__main__":
    main()
