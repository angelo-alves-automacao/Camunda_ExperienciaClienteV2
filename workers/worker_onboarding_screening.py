"""
External Task Worker: Onboarding - Realizar Screening de Saude
==============================================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Coleta dados de saude via conversa gamificada
- Processa documentos/exames via OCR
- Retorna dados coletados para estratificacao

O BPMN ja definiu que esta tarefa deve ser executada.
O codigo NAO decide caminhos do processo.

Topic: onboarding-realizar-screening
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

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
class ScreeningConfig:
    """Configuracoes do servico de screening."""
    api_bus_url: str = os.getenv("API_BUS_URL", "https://bus.austaclinicas.com.br/api")
    api_timeout: int = int(os.getenv("API_BUS_TIMEOUT_SECONDS", "30"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-onboarding-screening"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION", "30000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# CLIENTE DE SCREENING
# =============================================================================
class ScreeningClient:
    """
    Cliente para operacoes de screening de saude.
    NAO contem logica de negocio - apenas operacoes tecnicas.
    """

    def __init__(self, config: ScreeningConfig):
        self.config = config
        self._session = None

    def _get_session(self):
        """Obtem sessao HTTP reutilizavel."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        return self._session

    def coletar_dados_screening(self, beneficiario_id: str, respostas: dict) -> dict:
        """
        Processa respostas do screening e retorna dados estruturados.

        Args:
            beneficiario_id: ID do beneficiario
            respostas: Respostas coletadas do questionario

        Returns:
            Dados de saude estruturados
        """
        logger.info(f"Coletando dados de screening para beneficiario: {beneficiario_id}")

        # Extrai dados das respostas
        dados_saude = {
            "beneficiario_id": beneficiario_id,
            "data_coleta": datetime.now().isoformat(),
            "peso_kg": respostas.get("peso"),
            "altura_cm": respostas.get("altura"),
            "imc": self._calcular_imc(respostas.get("peso"), respostas.get("altura")),
            "fumante": respostas.get("fumante", False),
            "pratica_exercicio": respostas.get("pratica_exercicio", False),
            "frequencia_exercicio": respostas.get("frequencia_exercicio"),
            "consome_alcool": respostas.get("consome_alcool", False),
            "frequencia_alcool": respostas.get("frequencia_alcool"),
            "historico_familiar": respostas.get("historico_familiar", []),
            "medicamentos_uso": respostas.get("medicamentos", []),
            "alergias": respostas.get("alergias", []),
            "condicoes_preexistentes": respostas.get("condicoes_preexistentes", []),
            "ultima_consulta_data": respostas.get("ultima_consulta"),
            "vacinas_em_dia": respostas.get("vacinas_em_dia", False),
        }

        # Calcula score de saude baseado nos dados
        dados_saude["score_saude"] = self._calcular_score_saude(dados_saude)

        return dados_saude

    def _calcular_imc(self, peso: Optional[float], altura: Optional[float]) -> Optional[float]:
        """Calcula IMC."""
        if peso and altura and altura > 0:
            altura_m = altura / 100 if altura > 3 else altura
            return round(peso / (altura_m ** 2), 2)
        return None

    def _calcular_score_saude(self, dados: dict) -> float:
        """
        Calcula score de saude baseado nos dados coletados.
        Score de 0 a 100, onde 100 e melhor.
        """
        score = 100.0

        # Penalizacoes por fatores de risco
        if dados.get("fumante"):
            score -= 20

        if dados.get("consome_alcool") and dados.get("frequencia_alcool") == "DIARIO":
            score -= 15
        elif dados.get("consome_alcool"):
            score -= 5

        if not dados.get("pratica_exercicio"):
            score -= 15

        # IMC fora do ideal
        imc = dados.get("imc")
        if imc:
            if imc < 18.5 or imc > 30:
                score -= 15
            elif imc < 20 or imc > 25:
                score -= 5

        # Historico familiar
        historico = dados.get("historico_familiar", [])
        if "DIABETES" in historico:
            score -= 10
        if "CARDIACO" in historico:
            score -= 10
        if "CANCER" in historico:
            score -= 10

        # Condicoes preexistentes
        condicoes = dados.get("condicoes_preexistentes", [])
        score -= len(condicoes) * 5

        return max(0, min(100, score))

    def processar_documentos_ocr(self, beneficiario_id: str, documentos: list) -> dict:
        """
        Processa documentos medicos via OCR.

        Args:
            beneficiario_id: ID do beneficiario
            documentos: Lista de URLs/paths de documentos

        Returns:
            Dados extraidos dos documentos
        """
        logger.info(f"Processando {len(documentos)} documentos para beneficiario: {beneficiario_id}")

        # Simulacao de processamento OCR
        # Em producao, integrar com servico de Computer Vision
        dados_extraidos = {
            "documentos_processados": len(documentos),
            "exames_encontrados": [],
            "diagnosticos_encontrados": [],
            "medicamentos_encontrados": []
        }

        return dados_extraidos

    def close(self):
        """Libera recursos."""
        if self._session:
            self._session.close()
            self._session = None


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_realizar_screening(task: ExternalTask) -> TaskResult:
    """
    Handler para realizar screening de saude do beneficiario.

    INPUT (do processo Camunda):
    - beneficiario_id: String - ID do beneficiario
    - beneficiario_nome: String - Nome do beneficiario
    - respostas_screening: JSON - Respostas do questionario
    - documentos_urls: List[String] - URLs dos documentos enviados (opcional)

    OUTPUT (para o processo Camunda):
    - screening_status: String - SUCESSO/ERRO
    - dados_saude: JSON - Dados de saude coletados
    - score_saude: Float - Score de saude (0-100)
    - documentos_processados: Integer - Quantidade de documentos processados
    - screening_data_conclusao: String - Data/hora da conclusao
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    # 1. Recebe variaveis do processo
    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    beneficiario_nome = variables.get('beneficiario_nome')
    respostas_screening = variables.get('respostas_screening', {})
    documentos_urls = variables.get('documentos_urls', [])

    logger.info(f"Screening para: {beneficiario_nome} (ID: {beneficiario_id})")

    # 2. Validacao tecnica (NAO e regra de negocio)
    if not beneficiario_id:
        return TaskResult.failure(
            task,
            error_message="beneficiario_id e obrigatorio",
            error_details="O ID do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    # 3. Executa operacoes tecnicas
    client = ScreeningClient(ScreeningConfig())

    try:
        # Coleta dados do screening
        dados_saude = client.coletar_dados_screening(beneficiario_id, respostas_screening)

        # Processa documentos se houver
        dados_documentos = {}
        if documentos_urls:
            dados_documentos = client.processar_documentos_ocr(beneficiario_id, documentos_urls)

        logger.info(f"Screening concluido. Score de saude: {dados_saude['score_saude']}")

        # 4. Retorna resultado tecnico para o Camunda
        return TaskResult.success(task, {
            'screening_status': 'SUCESSO',
            'dados_saude': dados_saude,
            'score_saude': dados_saude['score_saude'],
            'documentos_processados': dados_documentos.get('documentos_processados', 0),
            'screening_data_conclusao': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erro tecnico no screening: {e}")
        return TaskResult.success(task, {
            'screening_status': 'ERRO',
            'screening_mensagem': str(e),
            'screening_data_conclusao': datetime.now().isoformat()
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
    logger.info("WORKER: Onboarding - Screening de Saude")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: onboarding-realizar-screening")
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
        topic_names="onboarding-realizar-screening",
        action=handle_realizar_screening
    )


if __name__ == "__main__":
    main()
