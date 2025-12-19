#!/usr/bin/env python
"""
Script de Deploy - Operadora Digital do Futuro
===============================================

Faz deploy dos arquivos BPMN e DMN no Camunda Engine.

Uso:
    python scripts/deploy.py [--all] [--bpmn] [--dmn]

Opcoes:
    --all   Deploy de todos os arquivos (padrao)
    --bpmn  Deploy apenas dos arquivos BPMN
    --dmn   Deploy apenas dos arquivos DMN
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Configuracao de paths
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_camunda_url() -> str:
    """Obtem URL do Camunda."""
    return os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")


def deploy_file(file_path: Path, deployment_name: str = None) -> dict:
    """
    Faz deploy de um arquivo no Camunda.

    Args:
        file_path: Caminho do arquivo
        deployment_name: Nome do deployment (opcional)

    Returns:
        Resultado do deploy
    """
    if not file_path.exists():
        logger.error(f"Arquivo nao encontrado: {file_path}")
        return {"success": False, "error": "Arquivo nao encontrado"}

    camunda_url = get_camunda_url()
    deploy_url = f"{camunda_url}/deployment/create"

    deployment_name = deployment_name or f"deploy-{file_path.stem}"

    logger.info(f"Fazendo deploy: {file_path.name}")
    logger.info(f"URL: {deploy_url}")

    try:
        with open(file_path, 'rb') as f:
            files = {
                'deployment-name': (None, deployment_name),
                'enable-duplicate-filtering': (None, 'true'),
                'deploy-changed-only': (None, 'true'),
                file_path.name: (file_path.name, f, 'application/octet-stream')
            }

            response = requests.post(deploy_url, files=files, timeout=60)

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"  SUCESSO! Deployment ID: {result.get('id')}")
                return {
                    "success": True,
                    "deployment_id": result.get('id'),
                    "name": result.get('name'),
                    "deployed_resources": list(result.get('deployedProcessDefinitions', {}).keys()) +
                                          list(result.get('deployedDecisionDefinitions', {}).keys())
                }
            else:
                logger.error(f"  ERRO! Status: {response.status_code}")
                logger.error(f"  Resposta: {response.text}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }

    except Exception as e:
        logger.error(f"  ERRO! {str(e)}")
        return {"success": False, "error": str(e)}


def deploy_all_bpmn() -> list:
    """Deploy de todos os arquivos BPMN."""
    bpmn_dir = PROJECT_ROOT / 'bpmn'
    results = []

    if not bpmn_dir.exists():
        logger.warning(f"Diretorio BPMN nao encontrado: {bpmn_dir}")
        return results

    for bpmn_file in bpmn_dir.glob('*.bpmn'):
        result = deploy_file(bpmn_file)
        results.append({
            "file": bpmn_file.name,
            **result
        })

    return results


def deploy_all_dmn() -> list:
    """Deploy de todos os arquivos DMN."""
    dmn_dir = PROJECT_ROOT / 'dmn'
    results = []

    if not dmn_dir.exists():
        logger.warning(f"Diretorio DMN nao encontrado: {dmn_dir}")
        return results

    for dmn_file in dmn_dir.glob('*.dmn'):
        result = deploy_file(dmn_file)
        results.append({
            "file": dmn_file.name,
            **result
        })

    return results


def check_camunda_connection() -> bool:
    """Verifica conexao com o Camunda."""
    camunda_url = get_camunda_url()

    try:
        response = requests.get(f"{camunda_url}/engine", timeout=10)
        if response.status_code == 200:
            engines = response.json()
            logger.info(f"Conectado ao Camunda: {engines[0].get('name', 'default')}")
            return True
        else:
            logger.error(f"Erro ao conectar: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Erro de conexao: {e}")
        return False


def print_summary(results: list):
    """Imprime resumo do deploy."""
    print("\n" + "=" * 60)
    print("RESUMO DO DEPLOY")
    print("=" * 60)

    success_count = sum(1 for r in results if r.get('success'))
    fail_count = len(results) - success_count

    for result in results:
        status = "OK" if result.get('success') else "ERRO"
        print(f"  [{status}] {result.get('file')}")
        if result.get('deployed_resources'):
            for resource in result.get('deployed_resources'):
                print(f"        -> {resource}")
        if result.get('error'):
            print(f"        Erro: {result.get('error')[:50]}")

    print("=" * 60)
    print(f"Total: {len(results)} | Sucesso: {success_count} | Falha: {fail_count}")
    print("=" * 60)


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Deploy de BPMN e DMN no Camunda'
    )
    parser.add_argument('--all', action='store_true', default=True,
                        help='Deploy de todos os arquivos')
    parser.add_argument('--bpmn', action='store_true',
                        help='Deploy apenas de BPMN')
    parser.add_argument('--dmn', action='store_true',
                        help='Deploy apenas de DMN')

    args = parser.parse_args()

    print("=" * 60)
    print("OPERADORA DIGITAL DO FUTURO - Deploy")
    print("=" * 60)
    print(f"Camunda URL: {get_camunda_url()}")
    print("=" * 60)

    # Verifica conexao
    if not check_camunda_connection():
        logger.error("Nao foi possivel conectar ao Camunda. Abortando.")
        sys.exit(1)

    results = []

    # Define o que fazer deploy
    if args.bpmn and not args.dmn:
        logger.info("\nFazendo deploy dos arquivos BPMN...")
        results.extend(deploy_all_bpmn())
    elif args.dmn and not args.bpmn:
        logger.info("\nFazendo deploy dos arquivos DMN...")
        results.extend(deploy_all_dmn())
    else:
        logger.info("\nFazendo deploy de todos os arquivos...")
        logger.info("\n[BPMN]")
        results.extend(deploy_all_bpmn())
        logger.info("\n[DMN]")
        results.extend(deploy_all_dmn())

    # Imprime resumo
    print_summary(results)

    # Retorna codigo de erro se houver falhas
    if any(not r.get('success') for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
