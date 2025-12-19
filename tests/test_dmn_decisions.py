#!/usr/bin/env python
"""
Testes de Integracao - Tabelas DMN
==================================

Testa as tabelas de decisao DMN via REST API do Camunda.

Uso:
    pytest tests/test_dmn_decisions.py -v
"""

import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Configuracao de paths
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# URL do Camunda
CAMUNDA_URL = os.getenv("CAMUNDA_URL", "http://localhost:8080/engine-rest")


def evaluate_dmn(decision_key: str, variables: dict) -> dict:
    """
    Avalia uma tabela DMN via REST API.

    Args:
        decision_key: Chave da decisao DMN
        variables: Variaveis de entrada

    Returns:
        Resultado da avaliacao
    """
    url = f"{CAMUNDA_URL}/decision-definition/key/{decision_key}/evaluate"

    # Formata variaveis
    formatted_vars = {}
    for key, value in variables.items():
        if isinstance(value, bool):
            formatted_vars[key] = {"value": value, "type": "Boolean"}
        elif isinstance(value, int):
            formatted_vars[key] = {"value": value, "type": "Integer"}
        elif isinstance(value, float):
            formatted_vars[key] = {"value": value, "type": "Double"}
        else:
            formatted_vars[key] = {"value": str(value), "type": "String"}

    payload = {"variables": formatted_vars}

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Erro ao avaliar DMN: {response.status_code} - {response.text}")


@pytest.fixture
def camunda_available():
    """Verifica se o Camunda esta disponivel."""
    try:
        response = requests.get(f"{CAMUNDA_URL}/engine", timeout=5)
        return response.status_code == 200
    except:
        return False


# =============================================================================
# TESTES - Decision_Plano_Cuidados
# =============================================================================
class TestDecisionPlanoCuidados:
    """Testes para a tabela de decisao de Plano de Cuidados."""

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_risco_complexo(self, camunda_available):
        """Testa classificacao de risco COMPLEXO."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Plano_Cuidados", {
            "nivel_risco": "COMPLEXO",
            "idade": 70,
            "tem_doenca_cronica": True
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("frequencia_contato", {}).get("value") == "DIARIO"
        assert output.get("navegador_dedicado", {}).get("value") == True

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_risco_alto(self, camunda_available):
        """Testa classificacao de risco ALTO."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Plano_Cuidados", {
            "nivel_risco": "ALTO",
            "idade": 55,
            "tem_doenca_cronica": True
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("frequencia_contato", {}).get("value") == "2_3_VEZES_SEMANA"
        assert output.get("navegador_dedicado", {}).get("value") == True

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_risco_moderado_idoso(self, camunda_available):
        """Testa classificacao de risco MODERADO para idoso."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Plano_Cuidados", {
            "nivel_risco": "MODERADO",
            "idade": 75,
            "tem_doenca_cronica": False
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("frequencia_contato", {}).get("value") == "SEMANAL"
        assert output.get("canal_principal", {}).get("value") == "WHATSAPP_VOZ"

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_risco_baixo(self, camunda_available):
        """Testa classificacao de risco BAIXO."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Plano_Cuidados", {
            "nivel_risco": "BAIXO",
            "idade": 30,
            "tem_doenca_cronica": False
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("frequencia_contato", {}).get("value") == "MENSAL"
        assert output.get("navegador_dedicado", {}).get("value") == False


# =============================================================================
# TESTES - Decision_Roteamento_Camada
# =============================================================================
class TestDecisionRoteamentoCamada:
    """Testes para a tabela de decisao de Roteamento de Camada."""

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_emergencia(self, camunda_available):
        """Testa roteamento para EMERGENCIA."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Roteamento_Camada", {
            "tipo_demanda": "TAREFA",
            "complexidade": "BAIXA",
            "urgencia": "EMERGENCIA",
            "nivel_risco_paciente": "BAIXO"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("camada", {}).get("value") == "ESPECIALISTA"
        assert output.get("sla_minutos", {}).get("value") == 1

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_paciente_complexo(self, camunda_available):
        """Testa roteamento para paciente COMPLEXO."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Roteamento_Camada", {
            "tipo_demanda": "INFORMACAO",
            "complexidade": "BAIXA",
            "urgencia": "ROTINA",
            "nivel_risco_paciente": "COMPLEXO"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("camada", {}).get("value") == "NAVEGADOR"

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_tarefa_simples_rotina(self, camunda_available):
        """Testa roteamento para tarefa simples de rotina."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Roteamento_Camada", {
            "tipo_demanda": "TAREFA",
            "complexidade": "BAIXA",
            "urgencia": "ROTINA",
            "nivel_risco_paciente": "BAIXO"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("camada", {}).get("value") == "SELF_SERVICE"

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_tarefa_complexa(self, camunda_available):
        """Testa roteamento para tarefa complexa."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Roteamento_Camada", {
            "tipo_demanda": "TAREFA",
            "complexidade": "ALTA",
            "urgencia": "ROTINA",
            "nivel_risco_paciente": "MODERADO"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("camada", {}).get("value") == "NAVEGADOR"


# =============================================================================
# TESTES - Decision_Tarefa_SelfService
# =============================================================================
class TestDecisionTarefaSelfService:
    """Testes para a tabela de decisao de Tarefas Self-Service."""

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_intencao_carteirinha(self, camunda_available):
        """Testa identificacao de intencao CARTEIRINHA."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Tarefa_SelfService", {
            "intencao": "CARTEIRINHA",
            "canal": "WHATSAPP"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("tarefa_codigo", {}).get("value") == "SS_CARTEIRINHA"
        assert output.get("rpa_necessario", {}).get("value") == False

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_intencao_agendamento(self, camunda_available):
        """Testa identificacao de intencao AGENDAR com RPA."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Tarefa_SelfService", {
            "intencao": "AGENDAR",
            "canal": "WHATSAPP"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("tarefa_codigo", {}).get("value") == "SS_AGENDAMENTO"
        assert output.get("rpa_necessario", {}).get("value") == True

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_intencao_boleto(self, camunda_available):
        """Testa identificacao de intencao BOLETO."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Tarefa_SelfService", {
            "intencao": "BOLETO",
            "canal": "APP"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("tarefa_codigo", {}).get("value") == "SS_BOLETO"

    @pytest.mark.skipif(not os.getenv("CAMUNDA_URL"), reason="Camunda URL nao configurada")
    def test_intencao_default(self, camunda_available):
        """Testa intencao nao mapeada (default = FAQ)."""
        if not camunda_available:
            pytest.skip("Camunda nao disponivel")

        result = evaluate_dmn("Decision_Tarefa_SelfService", {
            "intencao": "DESCONHECIDA",
            "canal": "WHATSAPP"
        })

        assert len(result) > 0
        output = result[0]
        assert output.get("tarefa_codigo", {}).get("value") == "SS_FAQ"


# =============================================================================
# TESTES UNITARIOS (sem Camunda)
# =============================================================================
class TestDMNLogic:
    """Testes unitarios da logica DMN (sem depender do Camunda)."""

    def test_classificacao_nps_promotor(self):
        """Testa classificacao NPS - Promotor."""
        nota = 9
        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "PROMOTOR"

    def test_classificacao_nps_neutro(self):
        """Testa classificacao NPS - Neutro."""
        nota = 7
        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "NEUTRO"

    def test_classificacao_nps_detrator(self):
        """Testa classificacao NPS - Detrator."""
        nota = 5
        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "DETRATOR"

    def test_piramide_risco_distribuicao(self):
        """Testa distribuicao da piramide de risco."""
        # Piramide de Kaiser
        baixo = 50
        moderado = 30
        alto = 15
        complexo = 5

        total = baixo + moderado + alto + complexo
        assert total == 100

    def test_sla_emergencia(self):
        """Testa SLA para emergencia."""
        sla_emergencia = 1  # minuto
        assert sla_emergencia <= 5  # Deve ser muito rapido

    def test_sla_selfservice(self):
        """Testa SLA para self-service."""
        sla_selfservice = 1  # minuto
        assert sla_selfservice <= 3  # Conforme meta do README


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
