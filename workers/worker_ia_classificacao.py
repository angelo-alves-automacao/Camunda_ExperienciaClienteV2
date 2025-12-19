"""
External Task Worker: IA - Classificacao e Roteamento
======================================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Identifica beneficiario via autenticacao automatica
- Classifica demanda usando GPT-4 (NLP)
- Retorna classificacao para o DMN decidir roteamento

O BPMN ja definiu que esta tarefa deve ser executada.
O DMN definira a camada de atendimento baseado na classificacao.
O codigo NAO decide caminhos do processo.

Topics:
- recepcao-identificar-beneficiario
- ia-classificar-demanda
- ia-processar-demanda
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
class IAConfig:
    """Configuracoes da IA (OpenAI)."""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    api_bus_url: str = os.getenv("API_BUS_URL", "https://bus.austaclinicas.com.br/api")


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-ia-classificacao"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION", "30000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE DE IDENTIFICACAO
# =============================================================================
class IdentificacaoClient:
    """
    Cliente para identificacao e autenticacao de beneficiarios.
    NAO contem logica de negocio.
    """

    def __init__(self, config: IAConfig):
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

    def identificar_por_telefone(self, telefone: str) -> dict:
        """
        Identifica beneficiario pelo telefone.

        Args:
            telefone: Numero do telefone

        Returns:
            Dados do beneficiario
        """
        logger.info(f"Identificando beneficiario pelo telefone: {telefone[-4:]}")

        session = self._get_session()

        try:
            url = f"{self.config.api_bus_url}/paciente/telefone/{telefone}"
            response = session.get(url, timeout=30)

            if response.status_code == 200:
                dados = response.json()
                return {
                    "identificado": True,
                    "beneficiario_id": dados.get("id"),
                    "beneficiario_nome": dados.get("nome"),
                    "cpf": dados.get("cpf"),
                    "convenio_codigo": dados.get("convenio_codigo"),
                    "plano": dados.get("plano"),
                    "nivel_risco": dados.get("nivel_risco", "BAIXO"),
                    "navegador_atribuido": dados.get("navegador_id")
                }
            else:
                return {
                    "identificado": False,
                    "motivo": "Beneficiario nao encontrado"
                }

        except Exception as e:
            logger.error(f"Erro ao identificar beneficiario: {e}")
            return {
                "identificado": False,
                "motivo": str(e)
            }

    def carregar_perfil_360(self, beneficiario_id: str) -> dict:
        """
        Carrega perfil 360 do beneficiario.

        Args:
            beneficiario_id: ID do beneficiario

        Returns:
            Perfil completo
        """
        logger.info(f"Carregando perfil 360 para: {beneficiario_id}")

        session = self._get_session()

        try:
            url = f"{self.config.api_bus_url}/paciente/{beneficiario_id}/perfil360"
            response = session.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                return {}

        except Exception as e:
            logger.error(f"Erro ao carregar perfil: {e}")
            return {}

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# CLIENTE DE CLASSIFICACAO (IA/NLP)
# =============================================================================
class ClassificacaoIAClient:
    """
    Cliente para classificacao de demandas usando IA.
    NAO contem logica de negocio - apenas operacoes tecnicas de NLP.
    """

    def __init__(self, config: IAConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        """Obtem cliente OpenAI."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.config.api_key)
            except Exception as e:
                logger.warning(f"Erro ao criar cliente OpenAI: {e}")
        return self._client

    def classificar_demanda(self, mensagem: str, contexto: dict = None) -> dict:
        """
        Classifica demanda do beneficiario usando NLP.

        Args:
            mensagem: Texto da mensagem do beneficiario
            contexto: Contexto adicional (historico, perfil)

        Returns:
            Classificacao da demanda
        """
        logger.info(f"Classificando demanda: {mensagem[:50]}...")

        client = self._get_client()

        if client:
            return self._classificar_com_gpt(mensagem, contexto)
        else:
            return self._classificar_com_regras(mensagem)

    def _classificar_com_gpt(self, mensagem: str, contexto: dict = None) -> dict:
        """Classifica usando GPT-4."""
        try:
            prompt = self._montar_prompt_classificacao(mensagem, contexto)

            response = self._client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                response_format={"type": "json_object"}
            )

            import json
            resultado = json.loads(response.choices[0].message.content)

            return {
                "tipo_demanda": resultado.get("tipo_demanda", "TAREFA"),
                "complexidade": resultado.get("complexidade", "MEDIA"),
                "urgencia": resultado.get("urgencia", "ROTINA"),
                "intencao": resultado.get("intencao", "GERAL"),
                "entidades": resultado.get("entidades", {}),
                "confianca": resultado.get("confianca", 0.8),
                "classificado_por": "GPT-4"
            }

        except Exception as e:
            logger.error(f"Erro na classificacao GPT: {e}")
            return self._classificar_com_regras(mensagem)

    def _classificar_com_regras(self, mensagem: str) -> dict:
        """Classifica usando regras simples (fallback)."""
        mensagem_lower = mensagem.lower()

        # Detecta urgencia/emergencia
        palavras_emergencia = ["emergencia", "urgente", "dor forte", "nao consigo respirar",
                               "acidente", "sangramento", "desmaio"]
        palavras_urgencia = ["dor", "febre", "mal estar", "preciso urgente", "rapido"]

        if any(p in mensagem_lower for p in palavras_emergencia):
            urgencia = "EMERGENCIA"
        elif any(p in mensagem_lower for p in palavras_urgencia):
            urgencia = "URGENTE"
        else:
            urgencia = "ROTINA"

        # Detecta tipo de demanda
        palavras_info = ["status", "resultado", "como esta", "qual", "onde",
                         "quando", "informacao", "saber"]
        palavras_reclamacao = ["reclamacao", "problema", "insatisfeito", "absurdo",
                               "demora", "pessimo"]
        palavras_tarefa = ["agendar", "cancelar", "solicitar", "pedir", "autorizar",
                           "segunda via", "boleto", "carteirinha"]

        if any(p in mensagem_lower for p in palavras_reclamacao):
            tipo_demanda = "RECLAMACAO"
        elif any(p in mensagem_lower for p in palavras_info):
            tipo_demanda = "INFORMACAO"
        elif any(p in mensagem_lower for p in palavras_tarefa):
            tipo_demanda = "TAREFA"
        else:
            tipo_demanda = "TAREFA"

        # Detecta intencao especifica
        intencao = self._detectar_intencao(mensagem_lower)

        # Define complexidade baseada na urgencia e tipo
        if urgencia == "EMERGENCIA" or tipo_demanda == "RECLAMACAO":
            complexidade = "ALTA"
        elif urgencia == "URGENTE":
            complexidade = "MEDIA"
        else:
            complexidade = "BAIXA"

        return {
            "tipo_demanda": tipo_demanda,
            "complexidade": complexidade,
            "urgencia": urgencia,
            "intencao": intencao,
            "entidades": {},
            "confianca": 0.6,
            "classificado_por": "REGRAS"
        }

    def _detectar_intencao(self, mensagem: str) -> str:
        """Detecta intencao especifica da mensagem."""
        intencoes = {
            "CARTEIRINHA": ["carteirinha", "cartao", "segunda via"],
            "BOLETO": ["boleto", "fatura", "pagamento", "mensalidade"],
            "STATUS_AUTORIZACAO": ["autorizacao", "guia", "aprovado"],
            "AGENDAR": ["agendar", "marcar", "consulta"],
            "CANCELAR": ["cancelar", "desmarcar"],
            "RESULTADO_EXAME": ["resultado", "exame", "laudo"],
            "REDE_CREDENCIADA": ["medico", "clinica", "hospital", "credenciado"],
            "COBERTURA": ["cobertura", "carencia", "cobre", "coberto"],
        }

        for intencao, palavras in intencoes.items():
            if any(p in mensagem for p in palavras):
                return intencao

        return "GERAL"

    def _montar_prompt_classificacao(self, mensagem: str, contexto: dict = None) -> dict:
        """Monta prompt para classificacao."""
        system = """Voce e um assistente de classificacao de demandas para uma operadora de saude.
Classifique a mensagem do beneficiario e retorne um JSON com:

{
  "tipo_demanda": "INFORMACAO|TAREFA|EMERGENCIA|RECLAMACAO",
  "complexidade": "BAIXA|MEDIA|ALTA|CRITICA",
  "urgencia": "ROTINA|URGENTE|EMERGENCIA",
  "intencao": "CODIGO_DA_INTENCAO",
  "entidades": {"procedimento": "...", "data": "...", etc},
  "confianca": 0.0-1.0
}

Intencoes possiveis:
- CARTEIRINHA: segunda via de carteirinha
- BOLETO: boleto, fatura, pagamento
- STATUS_AUTORIZACAO: status de autorizacao/guia
- AGENDAR: agendar consulta/exame
- CANCELAR: cancelar agendamento
- RESULTADO_EXAME: resultado de exames
- REDE_CREDENCIADA: busca de medicos/clinicas
- COBERTURA: duvidas sobre cobertura/carencia
- REEMBOLSO: solicitar reembolso
- EMERGENCIA_MEDICA: situacao de emergencia
- GERAL: outras demandas

EMERGENCIA: dor toracica, falta de ar, AVC, sangramento intenso, perda de consciencia
URGENTE: febre alta, dor moderada, mal estar, trauma leve"""

        user = f"Mensagem do beneficiario: {mensagem}"

        if contexto:
            user += f"\n\nContexto adicional: {contexto}"

        return {"system": system, "user": user}

    def processar_com_agente(self, mensagem: str, classificacao: dict, perfil: dict) -> dict:
        """
        Processa demanda com agente IA especializado.

        Args:
            mensagem: Mensagem do beneficiario
            classificacao: Classificacao da demanda
            perfil: Perfil do beneficiario

        Returns:
            Resultado do processamento
        """
        logger.info(f"Processando com agente IA - Intencao: {classificacao.get('intencao')}")

        # Aqui integraria com agentes especializados
        # Por hora, retorna que precisa de processamento adicional

        return {
            "processado": True,
            "ia_resolvido": classificacao.get("complexidade") == "BAIXA",
            "resposta_sugerida": None,
            "acao_necessaria": None
        }


# =============================================================================
# HANDLERS DOS EXTERNAL TASKS
# =============================================================================
def handle_identificar_beneficiario(task: ExternalTask) -> TaskResult:
    """
    Handler para identificar beneficiario.

    INPUT:
    - telefone_origem: String

    OUTPUT:
    - beneficiario_identificado: Boolean
    - beneficiario_id: String
    - beneficiario_nome: String
    - nivel_risco_paciente: String
    - perfil_360: JSON
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    telefone = variables.get('telefone_origem')

    if not telefone:
        return TaskResult.failure(
            task,
            error_message="telefone_origem e obrigatorio",
            error_details="O telefone de origem deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    config = IAConfig()
    client = IdentificacaoClient(config)

    try:
        # Identifica beneficiario
        resultado = client.identificar_por_telefone(telefone)

        if resultado.get("identificado"):
            # Carrega perfil 360
            perfil = client.carregar_perfil_360(resultado.get("beneficiario_id"))

            return TaskResult.success(task, {
                'beneficiario_identificado': True,
                'beneficiario_id': resultado.get('beneficiario_id'),
                'beneficiario_nome': resultado.get('beneficiario_nome'),
                'beneficiario_cpf': resultado.get('cpf'),
                'convenio_codigo': resultado.get('convenio_codigo'),
                'nivel_risco_paciente': resultado.get('nivel_risco', 'BAIXO'),
                'navegador_atribuido': resultado.get('navegador_atribuido'),
                'perfil_360': perfil
            })
        else:
            return TaskResult.success(task, {
                'beneficiario_identificado': False,
                'identificacao_motivo': resultado.get('motivo')
            })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'beneficiario_identificado': False,
            'identificacao_erro': str(e)
        })

    finally:
        client.close()


def handle_classificar_demanda(task: ExternalTask) -> TaskResult:
    """
    Handler para classificar demanda com IA.

    INPUT:
    - mensagem_beneficiario: String
    - beneficiario_id: String (opcional)
    - perfil_360: JSON (opcional)

    OUTPUT:
    - tipo_demanda: String
    - complexidade: String
    - urgencia: String
    - intencao: String
    - classificacao_confianca: Float
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    mensagem = variables.get('mensagem_beneficiario', '')
    perfil = variables.get('perfil_360', {})

    if not mensagem:
        return TaskResult.failure(
            task,
            error_message="mensagem_beneficiario e obrigatorio",
            error_details="A mensagem do beneficiario deve ser informada",
            retries=0,
            retry_timeout=5000
        )

    config = IAConfig()
    client = ClassificacaoIAClient(config)

    try:
        resultado = client.classificar_demanda(mensagem, perfil)

        return TaskResult.success(task, {
            'tipo_demanda': resultado.get('tipo_demanda'),
            'complexidade': resultado.get('complexidade'),
            'urgencia': resultado.get('urgencia'),
            'intencao': resultado.get('intencao'),
            'entidades_extraidas': resultado.get('entidades', {}),
            'classificacao_confianca': resultado.get('confianca'),
            'classificacao_metodo': resultado.get('classificado_por'),
            'classificacao_data': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'tipo_demanda': 'TAREFA',
            'complexidade': 'MEDIA',
            'urgencia': 'ROTINA',
            'intencao': 'GERAL',
            'classificacao_erro': str(e)
        })


def handle_processar_demanda(task: ExternalTask) -> TaskResult:
    """
    Handler para processar demanda com agente IA.

    INPUT:
    - mensagem_beneficiario: String
    - tipo_demanda: String
    - intencao: String
    - perfil_360: JSON

    OUTPUT:
    - ia_resolvido: Boolean
    - ia_resposta: String
    - ia_acao_necessaria: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    variables = task.get_variables()
    mensagem = variables.get('mensagem_beneficiario', '')
    classificacao = {
        'tipo_demanda': variables.get('tipo_demanda'),
        'complexidade': variables.get('complexidade'),
        'intencao': variables.get('intencao')
    }
    perfil = variables.get('perfil_360', {})

    config = IAConfig()
    client = ClassificacaoIAClient(config)

    try:
        resultado = client.processar_com_agente(mensagem, classificacao, perfil)

        return TaskResult.success(task, {
            'ia_resolvido': resultado.get('ia_resolvido', False),
            'ia_resposta': resultado.get('resposta_sugerida'),
            'ia_acao_necessaria': resultado.get('acao_necessaria'),
            'ia_processamento_data': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erro tecnico: {e}")
        return TaskResult.success(task, {
            'ia_resolvido': False,
            'ia_erro': str(e)
        })


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia o worker com multiplos topics."""
    config = CamundaConfig()

    logger.info("=" * 60)
    logger.info("WORKER: IA - Classificacao e Roteamento")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info("Topics:")
    logger.info("  - recepcao-identificar-beneficiario")
    logger.info("  - ia-classificar-demanda")
    logger.info("  - ia-processar-demanda")
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
        topic_names="recepcao-identificar-beneficiario",
        action=handle_identificar_beneficiario
    )

    worker.subscribe(
        topic_names="ia-classificar-demanda",
        action=handle_classificar_demanda
    )

    worker.subscribe(
        topic_names="ia-processar-demanda",
        action=handle_processar_demanda
    )


if __name__ == "__main__":
    main()
