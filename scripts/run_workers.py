#!/usr/bin/env python
"""
Script para Executar Workers - Operadora Digital do Futuro
==========================================================

Executa todos os workers ou workers especificos.

Uso:
    python scripts/run_workers.py --all
    python scripts/run_workers.py --worker=whatsapp
    python scripts/run_workers.py --worker=onboarding --worker=ml
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Configuracao de paths
PROJECT_ROOT = Path(__file__).parent.parent
WORKERS_DIR = PROJECT_ROOT / 'workers'
load_dotenv(PROJECT_ROOT / '.env')

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mapeamento de workers
WORKERS = {
    "onboarding": "worker_onboarding_screening.py",
    "whatsapp": "worker_whatsapp_comunicacao.py",
    "ml": "worker_ml_estratificacao.py",
    "classificacao": "worker_ia_classificacao.py",
    "autorizacao": "worker_autorizacao_inteligente.py",
    "navegacao": "worker_navegacao_cuidado.py",
    "followup": "worker_followup_nps.py",
    # Workers existentes do MVP
    "api-paciente": "worker_api_consulta_paciente.py",
    "oracle-autorizacao": "worker_oracle_autorizacao.py",
    "oracle-consulta": "worker_oracle_consulta_paciente.py",
    "oracle-notificacao": "worker_oracle_notificacao.py",
    "ibm-rpa": "worker_ibm_rpa_autorizacao.py",
}


def get_worker_path(worker_name: str) -> Path:
    """Obtem caminho do worker."""
    if worker_name in WORKERS:
        return WORKERS_DIR / WORKERS[worker_name]
    return WORKERS_DIR / worker_name


def run_worker(worker_path: Path) -> subprocess.Popen:
    """
    Executa um worker em um novo processo.

    Args:
        worker_path: Caminho do arquivo do worker

    Returns:
        Processo do worker
    """
    if not worker_path.exists():
        logger.error(f"Worker nao encontrado: {worker_path}")
        return None

    logger.info(f"Iniciando worker: {worker_path.name}")

    process = subprocess.Popen(
        [sys.executable, str(worker_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        bufsize=1,
        universal_newlines=True
    )

    return process


def run_all_workers() -> List[subprocess.Popen]:
    """Executa todos os workers."""
    processes = []

    for name, filename in WORKERS.items():
        worker_path = WORKERS_DIR / filename
        if worker_path.exists():
            process = run_worker(worker_path)
            if process:
                processes.append((name, process))
        else:
            logger.warning(f"Worker nao encontrado: {filename}")

    return processes


def monitor_processes(processes: List[tuple]):
    """
    Monitora processos em execucao.

    Args:
        processes: Lista de tuplas (nome, processo)
    """
    logger.info(f"\nMonitorando {len(processes)} workers...")
    logger.info("Pressione Ctrl+C para parar todos os workers.\n")

    try:
        while True:
            for name, process in processes:
                # Le output do processo
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        print(f"[{name}] {line.strip()}")

                # Verifica se o processo terminou
                if process.poll() is not None:
                    logger.warning(f"Worker '{name}' terminou com codigo {process.returncode}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("\nEncerrando workers...")
        for name, process in processes:
            logger.info(f"Parando worker: {name}")
            process.terminate()
            process.wait(timeout=5)
        logger.info("Todos os workers foram encerrados.")


def list_workers():
    """Lista workers disponiveis."""
    print("\nWorkers disponiveis:")
    print("=" * 50)

    for name, filename in WORKERS.items():
        worker_path = WORKERS_DIR / filename
        status = "OK" if worker_path.exists() else "NAO ENCONTRADO"
        print(f"  {name:20} [{status}]")

    print("=" * 50)


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Executar workers do Camunda'
    )

    parser.add_argument('--all', action='store_true',
                        help='Executa todos os workers')
    parser.add_argument('--worker', action='append', dest='workers',
                        help='Nome do worker para executar (pode repetir)')
    parser.add_argument('--list', action='store_true',
                        help='Lista workers disponiveis')

    args = parser.parse_args()

    print("=" * 60)
    print("OPERADORA DIGITAL DO FUTURO - Workers")
    print("=" * 60)
    print(f"Camunda URL: {os.getenv('CAMUNDA_URL')}")
    print("=" * 60)

    if args.list:
        list_workers()
        return

    processes = []

    if args.all:
        processes = run_all_workers()

    elif args.workers:
        for worker_name in args.workers:
            worker_path = get_worker_path(worker_name)
            process = run_worker(worker_path)
            if process:
                processes.append((worker_name, process))

    else:
        parser.print_help()
        print("\nExemplos:")
        print("  python scripts/run_workers.py --all")
        print("  python scripts/run_workers.py --worker=whatsapp")
        print("  python scripts/run_workers.py --list")
        return

    if not processes:
        logger.error("Nenhum worker foi iniciado.")
        sys.exit(1)

    print(f"\n{len(processes)} worker(s) iniciado(s):")
    for name, _ in processes:
        print(f"  - {name}")

    monitor_processes(processes)


if __name__ == "__main__":
    main()
