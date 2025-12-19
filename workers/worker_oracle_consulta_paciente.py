"""
External Task Worker: Oracle - Consulta Paciente
=================================================

Responsabilidade TÉCNICA (não contém regras de negócio):
- Conectar ao Oracle/Tasy
- Executar query de consulta
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
import oracledb

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / '.env')
from camunda.external_task.external_task import ExternalTask
from camunda.external_task.external_task_worker import ExternalTaskWorker

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÃO (deve vir de variáveis de ambiente em produção)
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
    worker_id: str = "oracle-worker-001"
    max_tasks: int = 1
    lock_duration: int = 30000  # 30 segundos
    sleep_seconds: int = 5


# =============================================================================
# REPOSITÓRIO ORACLE (apenas execução técnica)
# =============================================================================
class OraclePacienteRepository:
    """
    Repositório para acesso ao Oracle/Tasy.
    Executa apenas operações técnicas de banco de dados.
    NÃO contém lógica de negócio.
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

    def consultar_paciente_por_cpf(self, cpf: str) -> Optional[dict]:
        """
        Consulta paciente por CPF no Tasy.
        
        INPUT TÉCNICO:
        - cpf: String com CPF do paciente
        
        OUTPUT TÉCNICO:
        - dict com dados do paciente ou None
        """
        query = """
            SELECT 
                p.nr_sequencia AS paciente_id,
                p.nm_paciente AS paciente_nome,
                p.nr_cpf AS cpf,
                c.cd_convenio AS convenio_codigo,
                c.nm_convenio AS convenio_nome,
                CASE WHEN c.dt_validade >= SYSDATE THEN 'S' ELSE 'N' END AS plano_ativo
            FROM 
                tasy.paciente p
                LEFT JOIN tasy.convenio_paciente cp ON p.nr_sequencia = cp.nr_seq_paciente
                LEFT JOIN tasy.convenio c ON cp.cd_convenio = c.cd_convenio
            WHERE 
                p.nr_cpf = :cpf
                AND ROWNUM = 1
        """
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, {'cpf': cpf})
            row = cursor.fetchone()
            
            if row:
                return {
                    'paciente_id': str(row[0]),
                    'paciente_nome': row[1],
                    'cpf': row[2],
                    'convenio_codigo': row[3],
                    'convenio_nome': row[4],
                    'plano_ativo': row[5] == 'S'
                }
            return None
            
        except Exception as e:
            logger.error(f"Erro ao consultar paciente: {e}")
            raise

    def consultar_paciente_por_carteirinha(self, carteirinha: str) -> Optional[dict]:
        """
        Consulta paciente por número da carteirinha.
        
        INPUT TÉCNICO:
        - carteirinha: String com número da carteirinha
        
        OUTPUT TÉCNICO:
        - dict com dados do paciente ou None
        """
        query = """
            SELECT 
                p.nr_sequencia AS paciente_id,
                p.nm_paciente AS paciente_nome,
                p.nr_cpf AS cpf,
                c.cd_convenio AS convenio_codigo,
                c.nm_convenio AS convenio_nome,
                CASE WHEN c.dt_validade >= SYSDATE THEN 'S' ELSE 'N' END AS plano_ativo
            FROM 
                tasy.paciente p
                INNER JOIN tasy.convenio_paciente cp ON p.nr_sequencia = cp.nr_seq_paciente
                INNER JOIN tasy.convenio c ON cp.cd_convenio = c.cd_convenio
            WHERE 
                cp.nr_carteira = :carteirinha
                AND ROWNUM = 1
        """
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, {'carteirinha': carteirinha})
            row = cursor.fetchone()
            
            if row:
                return {
                    'paciente_id': str(row[0]),
                    'paciente_nome': row[1],
                    'cpf': row[2],
                    'convenio_codigo': row[3],
                    'convenio_nome': row[4],
                    'plano_ativo': row[5] == 'S'
                }
            return None
            
        except Exception as e:
            logger.error(f"Erro ao consultar paciente por carteirinha: {e}")
            raise

    def close(self):
        """Fecha conexão com o banco."""
        if self._connection:
            self._connection.close()
            self._connection = None


# =============================================================================
# HANDLER DO EXTERNAL TASK (apenas orquestração técnica)
# =============================================================================
def handle_consulta_paciente(task: ExternalTask) -> dict:
    """
    Handler para o External Task de consulta de paciente.
    
    RESPONSABILIDADE:
    - Receber variáveis do processo (cpf_paciente, carteirinha)
    - Executar consulta técnica no Oracle
    - Retornar resultados técnicos ao processo
    
    NÃO FAZ:
    - Decisões de negócio
    - Validações de elegibilidade
    - Controle de fluxo
    """
    logger.info(f"Processando task: {task.get_task_id()}")
    
    # Recebe variáveis do processo (já definidas pelo BPMN)
    variables = task.get_variables()
    cpf_paciente = variables.get('cpf_paciente')
    carteirinha = variables.get('carteirinha')
    
    logger.info(f"Consultando paciente - CPF: {cpf_paciente}, Carteirinha: {carteirinha}")
    
    # Execução técnica
    repository = OraclePacienteRepository(OracleConfig())
    
    try:
        # Tenta primeiro por CPF, depois por carteirinha
        paciente = None
        
        if cpf_paciente:
            paciente = repository.consultar_paciente_por_cpf(cpf_paciente)
        
        if not paciente and carteirinha:
            paciente = repository.consultar_paciente_por_carteirinha(carteirinha)
        
        # Retorna resultados técnicos ao processo
        # O BPMN decidirá o que fazer com esses dados
        if paciente:
            return {
                "paciente_encontrado": True,
                "paciente_id": paciente['paciente_id'],
                "paciente_nome": paciente['paciente_nome'],
                "convenio_codigo": paciente['convenio_codigo'],
                "convenio_nome": paciente['convenio_nome'],
                "plano_ativo": paciente['plano_ativo'],
                "consulta_timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "paciente_encontrado": False,
                "paciente_id": None,
                "paciente_nome": None,
                "convenio_codigo": None,
                "convenio_nome": None,
                "plano_ativo": False,
                "consulta_timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Erro técnico na consulta: {e}")
        # Retorna erro técnico - o BPMN tratará via boundary event
        raise
        
    finally:
        repository.close()


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
    
    # Subscreve no tópico
    worker.subscribe(
        topic_names="oracle-consulta-paciente",
        action=handle_consulta_paciente
    )


if __name__ == "__main__":
    main()
