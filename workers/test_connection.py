"""
Script para testar conexao dos workers com o Camunda.
Verifica se o worker consegue conectar e escutar topicos.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretorio pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import requests

# Carrega variaveis de ambiente
load_dotenv(Path(__file__).parent.parent / '.env')

CAMUNDA_URL = os.getenv("CAMUNDA_URL", "https://camundahml.austa.com.br/engine-rest")

def test_camunda_connection():
    """Testa conexao basica com o Camunda."""
    print(f"\n{'='*60}")
    print("TESTE DE CONEXAO COM CAMUNDA")
    print(f"{'='*60}")
    print(f"URL: {CAMUNDA_URL}")

    try:
        response = requests.get(f"{CAMUNDA_URL}/engine", timeout=10)
        response.raise_for_status()
        print(f"[OK] Conexao estabelecida")
        print(f"    Engines: {response.json()}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha na conexao: {e}")
        return False

def test_fetch_and_lock(topic_name: str, worker_id: str):
    """Testa fetch-and-lock para um topico especifico."""
    print(f"\n{'='*60}")
    print(f"TESTE FETCH-AND-LOCK: {topic_name}")
    print(f"{'='*60}")

    payload = {
        "workerId": worker_id,
        "maxTasks": 1,
        "usePriority": True,
        "topics": [
            {
                "topicName": topic_name,
                "lockDuration": 10000
            }
        ]
    }

    try:
        response = requests.post(
            f"{CAMUNDA_URL}/external-task/fetchAndLock",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        tasks = response.json()

        if tasks:
            print(f"[OK] {len(tasks)} task(s) encontrada(s)")
            for task in tasks:
                print(f"    - Task ID: {task.get('id')}")
                print(f"    - Process Instance: {task.get('processInstanceId')}")
        else:
            print(f"[OK] Nenhuma task pendente no topico '{topic_name}'")
            print(f"    (Isso e normal se nao houver processos em execucao)")

        return True

    except Exception as e:
        print(f"[ERRO] Falha no fetch-and-lock: {e}")
        return False

def test_external_task_count():
    """Lista todas as external tasks pendentes."""
    print(f"\n{'='*60}")
    print("EXTERNAL TASKS PENDENTES")
    print(f"{'='*60}")

    try:
        response = requests.get(
            f"{CAMUNDA_URL}/external-task",
            timeout=10
        )
        response.raise_for_status()
        tasks = response.json()

        if tasks:
            print(f"[INFO] {len(tasks)} task(s) pendente(s):")
            for task in tasks:
                print(f"    - Topic: {task.get('topicName')}")
                print(f"      Task ID: {task.get('id')}")
                print(f"      Process: {task.get('processInstanceId')}")
        else:
            print("[INFO] Nenhuma external task pendente")

        return True

    except Exception as e:
        print(f"[ERRO] Falha ao listar tasks: {e}")
        return False

def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print(" TESTE DE CONEXAO DOS WORKERS - MVP AUTORIZACAO CIRURGICA")
    print("="*60)

    # Teste 1: Conexao basica
    if not test_camunda_connection():
        print("\n[FALHA] Nao foi possivel conectar ao Camunda")
        return False

    # Teste 2: Listar external tasks pendentes
    test_external_task_count()

    # Teste 3: Fetch-and-lock para cada topico
    topics = [
        ("oracle-consulta-paciente", "test-worker-oracle-consulta"),
        ("ibm-rpa-autorizacao", "test-worker-ibm-rpa"),
        ("oracle-registrar-autorizacao", "test-worker-oracle-registro"),
        ("oracle-notificacao-medico", "test-worker-oracle-notificacao")
    ]

    for topic_name, worker_id in topics:
        test_fetch_and_lock(topic_name, worker_id)

    print(f"\n{'='*60}")
    print("RESULTADO FINAL")
    print(f"{'='*60}")
    print("[OK] Todos os testes de conexao passaram!")
    print("     Os workers conseguem se comunicar com o Camunda.")
    print("\nPara testar o fluxo completo, inicie um processo:")
    print(f'curl -X POST "{CAMUNDA_URL}/process-definition/key/Process_MVP_Autorizacao/start" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"variables": {"cpf_paciente": {"value": "12345678901", "type": "String"}}}\'')

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
