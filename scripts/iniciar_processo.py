#!/usr/bin/env python
"""
Script para Iniciar Processo - Operadora Digital do Futuro
==========================================================

Inicia uma nova instancia do processo de Coordenacao do Cuidado.

Uso:
    python scripts/iniciar_processo.py --novo-beneficiario --cpf=12345678900
    python scripts/iniciar_processo.py --contato --telefone=11999999999 --mensagem="Quero agendar consulta"
    python scripts/iniciar_processo.py --teste
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
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


def iniciar_processo(process_key: str, variables: dict, business_key: str = None) -> dict:
    """
    Inicia uma nova instancia do processo.

    Args:
        process_key: Chave do processo
        variables: Variaveis do processo
        business_key: Chave de negocio (opcional)

    Returns:
        Resultado da inicializacao
    """
    camunda_url = get_camunda_url()
    url = f"{camunda_url}/process-definition/key/{process_key}/start"

    # Formata variaveis para o formato do Camunda
    formatted_vars = {}
    for key, value in variables.items():
        if isinstance(value, bool):
            formatted_vars[key] = {"value": value, "type": "Boolean"}
        elif isinstance(value, int):
            formatted_vars[key] = {"value": value, "type": "Integer"}
        elif isinstance(value, float):
            formatted_vars[key] = {"value": value, "type": "Double"}
        elif isinstance(value, dict):
            formatted_vars[key] = {"value": json.dumps(value), "type": "Json"}
        else:
            formatted_vars[key] = {"value": str(value), "type": "String"}

    payload = {"variables": formatted_vars}
    if business_key:
        payload["businessKey"] = business_key

    logger.info(f"Iniciando processo: {process_key}")
    logger.info(f"Variaveis: {json.dumps(variables, indent=2, default=str)}")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"Processo iniciado com sucesso!")
            logger.info(f"Instance ID: {result.get('id')}")
            return {
                "success": True,
                "instance_id": result.get('id'),
                "business_key": result.get('businessKey'),
                "definition_id": result.get('definitionId')
            }
        else:
            logger.error(f"Erro ao iniciar processo: {response.status_code}")
            logger.error(f"Resposta: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }

    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"success": False, "error": str(e)}


def enviar_mensagem(message_name: str, variables: dict, correlation_key: str = None) -> dict:
    """
    Envia mensagem para o processo (para eventos de mensagem).

    Args:
        message_name: Nome da mensagem
        variables: Variaveis da mensagem
        correlation_key: Chave de correlacao

    Returns:
        Resultado do envio
    """
    camunda_url = get_camunda_url()
    url = f"{camunda_url}/message"

    # Formata variaveis
    formatted_vars = {}
    for key, value in variables.items():
        if isinstance(value, dict):
            formatted_vars[key] = {"value": json.dumps(value), "type": "Json"}
        else:
            formatted_vars[key] = {"value": str(value), "type": "String"}

    payload = {
        "messageName": message_name,
        "processVariables": formatted_vars,
        "resultEnabled": True
    }

    if correlation_key:
        payload["correlationKeys"] = {
            "businessKey": {"value": correlation_key, "type": "String"}
        }

    logger.info(f"Enviando mensagem: {message_name}")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            logger.info("Mensagem enviada com sucesso!")
            return {"success": True}
        elif response.status_code == 204:
            logger.info("Mensagem enviada (sem resposta)")
            return {"success": True}
        else:
            logger.error(f"Erro ao enviar mensagem: {response.status_code}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }

    except Exception as e:
        logger.error(f"Erro: {e}")
        return {"success": False, "error": str(e)}


def iniciar_novo_beneficiario(cpf: str, nome: str = None, telefone: str = None) -> dict:
    """
    Inicia processo para novo beneficiario (onboarding).

    Args:
        cpf: CPF do beneficiario
        nome: Nome do beneficiario
        telefone: Telefone do beneficiario

    Returns:
        Resultado
    """
    variables = {
        "beneficiario_cpf": cpf,
        "beneficiario_nome": nome or "Beneficiario Teste",
        "beneficiario_telefone": telefone or "11999999999",
        "data_inicio": datetime.now().isoformat(),
        "origem": "ONBOARDING"
    }

    return iniciar_processo(
        process_key="Process_Coordenacao_Cuidado",
        variables=variables,
        business_key=f"BEN-{cpf}"
    )


def iniciar_contato_beneficiario(telefone: str, mensagem: str) -> dict:
    """
    Inicia processo quando beneficiario entra em contato.

    Args:
        telefone: Telefone de origem
        mensagem: Mensagem do beneficiario

    Returns:
        Resultado
    """
    variables = {
        "telefone_origem": telefone,
        "mensagem_beneficiario": mensagem,
        "canal_entrada": "WHATSAPP",
        "data_contato": datetime.now().isoformat()
    }

    return enviar_mensagem(
        message_name="Message_ContatoRecebido",
        variables=variables
    )


def iniciar_processo_teste() -> dict:
    """
    Inicia processo com dados de teste.

    Returns:
        Resultado
    """
    logger.info("=" * 60)
    logger.info("INICIANDO PROCESSO DE TESTE")
    logger.info("=" * 60)

    variables = {
        # Dados do beneficiario
        "beneficiario_id": "TEST-001",
        "beneficiario_nome": "Maria Silva",
        "beneficiario_cpf": "12345678900",
        "beneficiario_telefone": "11999999999",

        # Dados de saude (screening)
        "respostas_screening": {
            "peso": 70,
            "altura": 165,
            "fumante": False,
            "pratica_exercicio": True,
            "frequencia_exercicio": "3_VEZES_SEMANA",
            "historico_familiar": ["DIABETES"],
            "medicamentos": [],
            "condicoes_preexistentes": [],
            "vacinas_em_dia": True
        },
        "idade": 45,

        # Configuracao
        "data_inicio": datetime.now().isoformat(),
        "origem": "TESTE",

        # Intervalo de monitoramento (para o timer)
        "intervalo_monitoramento": "PT1H",  # 1 hora
        "continuar_monitoramento": True
    }

    return iniciar_processo(
        process_key="Process_Coordenacao_Cuidado",
        variables=variables,
        business_key=f"TESTE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )


def listar_processos_ativos() -> list:
    """
    Lista processos ativos.

    Returns:
        Lista de processos
    """
    camunda_url = get_camunda_url()
    url = f"{camunda_url}/process-instance"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return []


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Iniciar processo no Camunda'
    )

    # Tipos de inicializacao
    parser.add_argument('--novo-beneficiario', action='store_true',
                        help='Inicia processo de onboarding')
    parser.add_argument('--contato', action='store_true',
                        help='Simula contato do beneficiario')
    parser.add_argument('--teste', action='store_true',
                        help='Inicia processo com dados de teste')
    parser.add_argument('--listar', action='store_true',
                        help='Lista processos ativos')

    # Parametros
    parser.add_argument('--cpf', type=str, help='CPF do beneficiario')
    parser.add_argument('--nome', type=str, help='Nome do beneficiario')
    parser.add_argument('--telefone', type=str, help='Telefone do beneficiario')
    parser.add_argument('--mensagem', type=str, help='Mensagem do beneficiario')

    args = parser.parse_args()

    print("=" * 60)
    print("OPERADORA DIGITAL DO FUTURO - Iniciar Processo")
    print("=" * 60)
    print(f"Camunda URL: {get_camunda_url()}")
    print("=" * 60)

    if args.listar:
        processos = listar_processos_ativos()
        print(f"\nProcessos ativos: {len(processos)}")
        for p in processos[:10]:
            print(f"  - {p.get('id')} ({p.get('businessKey', 'N/A')})")
        return

    if args.novo_beneficiario:
        if not args.cpf:
            print("Erro: --cpf e obrigatorio para --novo-beneficiario")
            sys.exit(1)
        result = iniciar_novo_beneficiario(
            cpf=args.cpf,
            nome=args.nome,
            telefone=args.telefone
        )

    elif args.contato:
        if not args.telefone or not args.mensagem:
            print("Erro: --telefone e --mensagem sao obrigatorios para --contato")
            sys.exit(1)
        result = iniciar_contato_beneficiario(
            telefone=args.telefone,
            mensagem=args.mensagem
        )

    elif args.teste:
        result = iniciar_processo_teste()

    else:
        parser.print_help()
        return

    # Imprime resultado
    print("\n" + "=" * 60)
    if result.get("success"):
        print("PROCESSO INICIADO COM SUCESSO!")
        print(f"Instance ID: {result.get('instance_id', 'N/A')}")
        print(f"Business Key: {result.get('business_key', 'N/A')}")
    else:
        print("ERRO AO INICIAR PROCESSO!")
        print(f"Erro: {result.get('error', 'Desconhecido')}")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
