"""
External Task Worker: ML - Estratificacao de Risco
===================================================

Responsabilidade TECNICA (nao contem regras de negocio):
- Executa modelo XGBoost para estratificacao de risco
- Processa features do beneficiario
- Retorna nivel de risco calculado

O BPMN ja definiu que esta tarefa deve ser executada.
O DMN definira o plano de cuidados baseado no risco.
O codigo NAO decide caminhos do processo.

Topic: ml-estratificar-risco
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
class MLConfig:
    """Configuracoes do modelo de ML."""
    model_path: str = os.getenv("ML_MODEL_PATH", "./models/estratificacao_risco.pkl")
    threshold_alto_risco: float = float(os.getenv("ML_THRESHOLD_ALTO_RISCO", "0.7"))
    threshold_medio_risco: float = float(os.getenv("ML_THRESHOLD_MEDIO_RISCO", "0.4"))


@dataclass
class CamundaConfig:
    """Configuracoes de conexao com Camunda."""
    base_url: str = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")
    worker_id: str = "worker-ml-estratificacao"
    max_tasks: int = int(os.getenv("WORKER_MAX_TASKS", "1"))
    lock_duration: int = int(os.getenv("WORKER_LOCK_DURATION_EXTENDED", "600000"))
    sleep_seconds: int = int(os.getenv("WORKER_SLEEP_SECONDS", "5"))


# =============================================================================
# MODELO DE ESTRATIFICACAO
# =============================================================================
class EstratificacaoRiscoModel:
    """
    Modelo de estratificacao de risco usando XGBoost.
    NAO contem logica de negocio - apenas operacoes tecnicas de ML.

    Piramide de Kaiser (aproximada):
    - COMPLEXO (5%): Score >= 0.85
    - ALTO (15%): Score >= 0.70
    - MODERADO (30%): Score >= 0.40
    - BAIXO (50%): Score < 0.40
    """

    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self._carregar_modelo()

    def _carregar_modelo(self):
        """Carrega modelo treinado."""
        try:
            import joblib
            if os.path.exists(self.config.model_path):
                self.model = joblib.load(self.config.model_path)
                logger.info(f"Modelo carregado de: {self.config.model_path}")
            else:
                logger.warning(f"Modelo nao encontrado em: {self.config.model_path}")
                logger.info("Usando modelo baseado em regras como fallback")
        except Exception as e:
            logger.warning(f"Erro ao carregar modelo: {e}")
            logger.info("Usando modelo baseado em regras como fallback")

    def extrair_features(self, dados_saude: Dict, dados_utilizacao: Dict) -> Dict:
        """
        Extrai features para o modelo.

        Args:
            dados_saude: Dados do screening de saude
            dados_utilizacao: Historico de utilizacao

        Returns:
            Features processadas
        """
        features = {
            # Features demograficas
            "idade": dados_saude.get("idade", 0),
            "sexo": 1 if dados_saude.get("sexo") == "M" else 0,

            # Features de saude
            "imc": dados_saude.get("imc", 25.0),
            "fumante": 1 if dados_saude.get("fumante") else 0,
            "pratica_exercicio": 1 if dados_saude.get("pratica_exercicio") else 0,
            "score_saude": dados_saude.get("score_saude", 50),

            # Features de condicoes
            "num_condicoes_cronicas": len(dados_saude.get("condicoes_preexistentes", [])),
            "tem_diabetes": 1 if "DIABETES" in dados_saude.get("condicoes_preexistentes", []) else 0,
            "tem_hipertensao": 1 if "HIPERTENSAO" in dados_saude.get("condicoes_preexistentes", []) else 0,
            "tem_cardiaco": 1 if "CARDIACO" in dados_saude.get("condicoes_preexistentes", []) else 0,
            "num_medicamentos": len(dados_saude.get("medicamentos_uso", [])),

            # Features de historico familiar
            "historico_diabetes": 1 if "DIABETES" in dados_saude.get("historico_familiar", []) else 0,
            "historico_cardiaco": 1 if "CARDIACO" in dados_saude.get("historico_familiar", []) else 0,
            "historico_cancer": 1 if "CANCER" in dados_saude.get("historico_familiar", []) else 0,

            # Features de utilizacao
            "num_internacoes_12m": dados_utilizacao.get("internacoes_12m", 0),
            "num_consultas_12m": dados_utilizacao.get("consultas_12m", 0),
            "num_exames_12m": dados_utilizacao.get("exames_12m", 0),
            "custo_12m": dados_utilizacao.get("custo_12m", 0),
            "dias_ultima_consulta": dados_utilizacao.get("dias_ultima_consulta", 365),
        }

        return features

    def predizer_risco(self, features: Dict) -> Dict:
        """
        Executa predicao de risco.

        Args:
            features: Features processadas

        Returns:
            Score de risco e nivel classificado
        """
        if self.model:
            # Usa modelo treinado
            try:
                import numpy as np
                feature_array = np.array([list(features.values())])
                score = self.model.predict_proba(feature_array)[0][1]
            except Exception as e:
                logger.warning(f"Erro na predicao: {e}")
                score = self._calcular_score_regras(features)
        else:
            # Fallback: modelo baseado em regras
            score = self._calcular_score_regras(features)

        # Classifica nivel de risco
        nivel_risco = self._classificar_nivel(score)

        return {
            "score_risco": round(score, 4),
            "nivel_risco": nivel_risco,
            "features_utilizadas": list(features.keys()),
            "modelo_versao": "1.0.0"
        }

    def _calcular_score_regras(self, features: Dict) -> float:
        """
        Calcula score de risco baseado em regras.
        Usado como fallback quando modelo ML nao esta disponivel.
        """
        score = 0.0

        # Idade
        idade = features.get("idade", 0)
        if idade >= 75:
            score += 0.25
        elif idade >= 65:
            score += 0.15
        elif idade >= 55:
            score += 0.08

        # Condicoes cronicas
        num_condicoes = features.get("num_condicoes_cronicas", 0)
        score += min(num_condicoes * 0.12, 0.36)

        # Condicoes especificas
        if features.get("tem_diabetes"):
            score += 0.10
        if features.get("tem_hipertensao"):
            score += 0.08
        if features.get("tem_cardiaco"):
            score += 0.15

        # Medicamentos
        num_meds = features.get("num_medicamentos", 0)
        if num_meds >= 5:
            score += 0.10
        elif num_meds >= 3:
            score += 0.05

        # Internacoes recentes
        internacoes = features.get("num_internacoes_12m", 0)
        if internacoes >= 2:
            score += 0.20
        elif internacoes >= 1:
            score += 0.10

        # Score de saude baixo
        score_saude = features.get("score_saude", 50)
        if score_saude < 40:
            score += 0.10
        elif score_saude < 60:
            score += 0.05

        # Estilo de vida
        if features.get("fumante"):
            score += 0.08
        if not features.get("pratica_exercicio"):
            score += 0.05

        # IMC
        imc = features.get("imc", 25)
        if imc >= 35:
            score += 0.10
        elif imc >= 30:
            score += 0.05

        return min(score, 1.0)

    def _classificar_nivel(self, score: float) -> str:
        """Classifica nivel de risco baseado no score."""
        if score >= 0.85:
            return "COMPLEXO"
        elif score >= self.config.threshold_alto_risco:
            return "ALTO"
        elif score >= self.config.threshold_medio_risco:
            return "MODERADO"
        else:
            return "BAIXO"


# =============================================================================
# HANDLER DO EXTERNAL TASK
# =============================================================================
def handle_estratificar_risco(task: ExternalTask) -> TaskResult:
    """
    Handler para estratificacao de risco do beneficiario.

    INPUT (do processo Camunda):
    - beneficiario_id: String
    - dados_saude: JSON (do screening)
    - dados_utilizacao: JSON (historico de uso - opcional)
    - idade: Integer

    OUTPUT (para o processo Camunda):
    - ml_status: String - SUCESSO/ERRO
    - score_risco: Float - Score de 0 a 1
    - nivel_risco: String - BAIXO/MODERADO/ALTO/COMPLEXO
    - ml_modelo_versao: String
    - ml_data_calculo: String
    """
    logger.info(f"Processando task: {task.get_task_id()}")

    # 1. Recebe variaveis do processo
    variables = task.get_variables()
    beneficiario_id = variables.get('beneficiario_id')
    dados_saude = variables.get('dados_saude', {})
    dados_utilizacao = variables.get('dados_utilizacao', {})
    idade = variables.get('idade', dados_saude.get('idade', 0))

    logger.info(f"Estratificando risco para beneficiario: {beneficiario_id}")

    # 2. Validacao tecnica
    if not beneficiario_id:
        return TaskResult.failure(
            task,
            error_message="beneficiario_id e obrigatorio",
            error_details="O ID do beneficiario deve ser informado",
            retries=0,
            retry_timeout=5000
        )

    # Adiciona idade aos dados de saude se nao estiver
    if 'idade' not in dados_saude:
        dados_saude['idade'] = idade

    # 3. Executa predicao
    config = MLConfig()
    model = EstratificacaoRiscoModel(config)

    try:
        # Extrai features
        features = model.extrair_features(dados_saude, dados_utilizacao)

        # Prediz risco
        resultado = model.predizer_risco(features)

        logger.info(f"Risco calculado: {resultado['nivel_risco']} (score: {resultado['score_risco']})")

        # 4. Retorna resultado tecnico para o Camunda
        return TaskResult.success(task, {
            'ml_status': 'SUCESSO',
            'score_risco': resultado['score_risco'],
            'nivel_risco': resultado['nivel_risco'],
            'ml_modelo_versao': resultado['modelo_versao'],
            'ml_data_calculo': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erro tecnico na estratificacao: {e}")
        return TaskResult.success(task, {
            'ml_status': 'ERRO',
            'ml_mensagem_erro': str(e),
            'nivel_risco': 'MODERADO',  # Fallback seguro
            'score_risco': 0.5,
            'ml_data_calculo': datetime.now().isoformat()
        })


# =============================================================================
# WORKER PRINCIPAL
# =============================================================================
def main():
    """Inicia o worker."""
    config = CamundaConfig()

    logger.info("=" * 60)
    logger.info("WORKER: ML - Estratificacao de Risco")
    logger.info("=" * 60)
    logger.info(f"Conectando em: {config.base_url}")
    logger.info(f"Topic: ml-estratificar-risco")
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
        topic_names="ml-estratificar-risco",
        action=handle_estratificar_risco
    )


if __name__ == "__main__":
    main()
