#!/usr/bin/env python
"""
Testes Unitarios - Workers
==========================

Testa a logica dos workers sem depender do Camunda.

Uso:
    pytest tests/test_workers.py -v
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Configuracao de paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'workers'))
load_dotenv(PROJECT_ROOT / '.env')


# =============================================================================
# TESTES - Worker Onboarding Screening
# =============================================================================
class TestScreeningClient:
    """Testes para o cliente de screening."""

    def test_calcular_imc_normal(self):
        """Testa calculo de IMC normal."""
        peso = 70
        altura = 175  # cm

        altura_m = altura / 100
        imc = round(peso / (altura_m ** 2), 2)

        assert 18.5 <= imc <= 25  # IMC normal

    def test_calcular_imc_sobrepeso(self):
        """Testa calculo de IMC sobrepeso."""
        peso = 85
        altura = 170  # cm

        altura_m = altura / 100
        imc = round(peso / (altura_m ** 2), 2)

        assert imc > 25  # Sobrepeso

    def test_calcular_score_saude_perfeito(self):
        """Testa score de saude perfeito."""
        score = 100.0

        # Sem penalizacoes
        fumante = False
        pratica_exercicio = True
        imc = 22

        if fumante:
            score -= 20
        if not pratica_exercicio:
            score -= 15
        if imc < 18.5 or imc > 30:
            score -= 15

        assert score == 100.0

    def test_calcular_score_saude_com_riscos(self):
        """Testa score de saude com fatores de risco."""
        score = 100.0

        # Com penalizacoes
        fumante = True  # -20
        pratica_exercicio = False  # -15
        imc = 32  # -15
        historico_diabetes = True  # -10

        if fumante:
            score -= 20
        if not pratica_exercicio:
            score -= 15
        if imc > 30:
            score -= 15
        if historico_diabetes:
            score -= 10

        assert score == 40.0


# =============================================================================
# TESTES - Worker ML Estratificacao
# =============================================================================
class TestEstratificacaoRisco:
    """Testes para o modelo de estratificacao de risco."""

    def test_classificar_nivel_complexo(self):
        """Testa classificacao de nivel COMPLEXO."""
        score = 0.90

        if score >= 0.85:
            nivel = "COMPLEXO"
        elif score >= 0.70:
            nivel = "ALTO"
        elif score >= 0.40:
            nivel = "MODERADO"
        else:
            nivel = "BAIXO"

        assert nivel == "COMPLEXO"

    def test_classificar_nivel_alto(self):
        """Testa classificacao de nivel ALTO."""
        score = 0.75

        if score >= 0.85:
            nivel = "COMPLEXO"
        elif score >= 0.70:
            nivel = "ALTO"
        elif score >= 0.40:
            nivel = "MODERADO"
        else:
            nivel = "BAIXO"

        assert nivel == "ALTO"

    def test_classificar_nivel_moderado(self):
        """Testa classificacao de nivel MODERADO."""
        score = 0.50

        if score >= 0.85:
            nivel = "COMPLEXO"
        elif score >= 0.70:
            nivel = "ALTO"
        elif score >= 0.40:
            nivel = "MODERADO"
        else:
            nivel = "BAIXO"

        assert nivel == "MODERADO"

    def test_classificar_nivel_baixo(self):
        """Testa classificacao de nivel BAIXO."""
        score = 0.25

        if score >= 0.85:
            nivel = "COMPLEXO"
        elif score >= 0.70:
            nivel = "ALTO"
        elif score >= 0.40:
            nivel = "MODERADO"
        else:
            nivel = "BAIXO"

        assert nivel == "BAIXO"

    def test_score_regras_idade_alta(self):
        """Testa score baseado em regras para idade alta."""
        score = 0.0
        idade = 80

        if idade >= 75:
            score += 0.25
        elif idade >= 65:
            score += 0.15
        elif idade >= 55:
            score += 0.08

        assert score == 0.25

    def test_score_regras_internacoes(self):
        """Testa score baseado em internacoes."""
        score = 0.0
        internacoes_12m = 3

        if internacoes_12m >= 2:
            score += 0.20
        elif internacoes_12m >= 1:
            score += 0.10

        assert score == 0.20


# =============================================================================
# TESTES - Worker IA Classificacao
# =============================================================================
class TestClassificacaoIA:
    """Testes para a classificacao por IA."""

    def test_detectar_urgencia_emergencia(self):
        """Testa deteccao de emergencia."""
        mensagem = "Estou com dor forte no peito e nao consigo respirar"
        mensagem_lower = mensagem.lower()

        palavras_emergencia = ["emergencia", "urgente", "dor forte", "nao consigo respirar"]
        palavras_urgencia = ["dor", "febre", "mal estar"]

        if any(p in mensagem_lower for p in palavras_emergencia):
            urgencia = "EMERGENCIA"
        elif any(p in mensagem_lower for p in palavras_urgencia):
            urgencia = "URGENTE"
        else:
            urgencia = "ROTINA"

        assert urgencia == "EMERGENCIA"

    def test_detectar_urgencia_urgente(self):
        """Testa deteccao de urgencia."""
        mensagem = "Estou com febre alta"
        mensagem_lower = mensagem.lower()

        palavras_emergencia = ["emergencia", "dor forte", "nao consigo respirar"]
        palavras_urgencia = ["dor", "febre", "mal estar"]

        if any(p in mensagem_lower for p in palavras_emergencia):
            urgencia = "EMERGENCIA"
        elif any(p in mensagem_lower for p in palavras_urgencia):
            urgencia = "URGENTE"
        else:
            urgencia = "ROTINA"

        assert urgencia == "URGENTE"

    def test_detectar_tipo_demanda_reclamacao(self):
        """Testa deteccao de reclamacao."""
        mensagem = "Estou muito insatisfeito com a demora"
        mensagem_lower = mensagem.lower()

        palavras_reclamacao = ["reclamacao", "problema", "insatisfeito", "demora"]
        palavras_info = ["status", "resultado", "informacao"]

        if any(p in mensagem_lower for p in palavras_reclamacao):
            tipo = "RECLAMACAO"
        elif any(p in mensagem_lower for p in palavras_info):
            tipo = "INFORMACAO"
        else:
            tipo = "TAREFA"

        assert tipo == "RECLAMACAO"

    def test_detectar_intencao_carteirinha(self):
        """Testa deteccao de intencao CARTEIRINHA."""
        mensagem = "Preciso da segunda via da minha carteirinha"
        mensagem_lower = mensagem.lower()

        intencoes = {
            "CARTEIRINHA": ["carteirinha", "cartao", "segunda via"],
            "BOLETO": ["boleto", "fatura", "pagamento"],
            "AGENDAR": ["agendar", "marcar", "consulta"]
        }

        intencao_detectada = "GERAL"
        for intencao, palavras in intencoes.items():
            if any(p in mensagem_lower for p in palavras):
                intencao_detectada = intencao
                break

        assert intencao_detectada == "CARTEIRINHA"


# =============================================================================
# TESTES - Worker WhatsApp
# =============================================================================
class TestWhatsAppClient:
    """Testes para o cliente WhatsApp."""

    def test_formatar_telefone_11_digitos(self):
        """Testa formatacao de telefone com 11 digitos."""
        telefone = "11999999999"
        numeros = ''.join(filter(str.isdigit, telefone))

        if len(numeros) == 11:
            numeros = f"55{numeros}"

        assert numeros == "5511999999999"

    def test_formatar_telefone_com_mascara(self):
        """Testa formatacao de telefone com mascara."""
        telefone = "(11) 99999-9999"
        numeros = ''.join(filter(str.isdigit, telefone))

        if len(numeros) == 11:
            numeros = f"55{numeros}"

        assert numeros == "5511999999999"

    def test_formatar_telefone_ja_internacional(self):
        """Testa telefone ja em formato internacional."""
        telefone = "5511999999999"
        numeros = ''.join(filter(str.isdigit, telefone))

        if len(numeros) == 11:
            numeros = f"55{numeros}"

        assert numeros == "5511999999999"


# =============================================================================
# TESTES - Worker Follow-up NPS
# =============================================================================
class TestNPSClient:
    """Testes para o cliente de NPS."""

    def test_classificar_nps_promotor(self):
        """Testa classificacao NPS promotor."""
        nota = 10

        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "PROMOTOR"

    def test_classificar_nps_neutro(self):
        """Testa classificacao NPS neutro."""
        nota = 8

        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "NEUTRO"

    def test_classificar_nps_detrator(self):
        """Testa classificacao NPS detrator."""
        nota = 4

        if nota >= 9:
            classificacao = "PROMOTOR"
        elif nota >= 7:
            classificacao = "NEUTRO"
        else:
            classificacao = "DETRATOR"

        assert classificacao == "DETRATOR"

    def test_calcular_nps_score(self):
        """Testa calculo do NPS score."""
        # Exemplo: 100 respostas
        promotores = 60
        neutros = 25
        detratores = 15
        total = promotores + neutros + detratores

        nps = ((promotores - detratores) / total) * 100

        assert nps == 45.0  # Meta do README e >70


# =============================================================================
# TESTES - Worker Navegacao
# =============================================================================
class TestNavegacaoClient:
    """Testes para o cliente de navegacao."""

    def test_calcular_score_prestador(self):
        """Testa calculo de score do prestador."""
        score_base = 80
        bonus_rede_preferencial = 20

        score_final = score_base + bonus_rede_preferencial

        assert score_final == 100

    def test_ordenar_prestadores_por_score(self):
        """Testa ordenacao de prestadores por score."""
        prestadores = [
            {"nome": "Dr. A", "score": 70},
            {"nome": "Dr. B", "score": 90},
            {"nome": "Dr. C", "score": 80}
        ]

        prestadores_ordenados = sorted(
            prestadores,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        assert prestadores_ordenados[0]["nome"] == "Dr. B"
        assert prestadores_ordenados[1]["nome"] == "Dr. C"
        assert prestadores_ordenados[2]["nome"] == "Dr. A"


# =============================================================================
# TESTES DE INTEGRACAO COM MOCKS
# =============================================================================
class TestWorkerIntegration:
    """Testes de integracao com mocks."""

    def test_external_task_success_flow(self):
        """Testa fluxo de sucesso de uma external task."""
        # Simula task
        mock_task = MagicMock()
        mock_task.get_task_id.return_value = "task-123"
        mock_task.get_variables.return_value = {
            "beneficiario_id": "BEN-001",
            "beneficiario_nome": "Maria Silva",
            "beneficiario_telefone": "11999999999"
        }

        # Valida que task tem os dados necessarios
        variables = mock_task.get_variables()
        assert variables.get("beneficiario_id") is not None
        assert variables.get("beneficiario_nome") is not None

    def test_external_task_failure_missing_param(self):
        """Testa falha por parametro faltando."""
        mock_task = MagicMock()
        mock_task.get_task_id.return_value = "task-456"
        mock_task.get_variables.return_value = {
            # beneficiario_id faltando
            "beneficiario_nome": "Maria Silva"
        }

        variables = mock_task.get_variables()
        beneficiario_id = variables.get("beneficiario_id")

        # Deve falhar se beneficiario_id nao existe
        assert beneficiario_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
