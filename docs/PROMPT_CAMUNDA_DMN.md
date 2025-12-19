# Prompt: DMN (Decision Model and Notation) no Camunda 7

Este documento contém o prompt padrão para criar tabelas de decisão DMN compatíveis com Camunda 7.

---

## Prompt para Geração de DMN Camunda 7

```
Crie uma tabela de decisão DMN para Camunda 7.

## Contexto Técnico

### Versão DMN - CRÍTICO!

O Camunda 7 usa DMN 1.1/1.2. Se criar DMN com versão 1.3 (padrão do Modeler novo),
o deploy FALHA com erro de parsing.

**ERRO COMUM:**
```
ENGINE-09005 Could not parse DMN: SAXException while parsing input
```

**Namespace CORRETO (DMN 1.1 - Camunda 7):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20180521/MODEL/"
             xmlns:dmndi="https://www.omg.org/spec/DMN/20180521/DMNDI/"
             xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/"
             xmlns:camunda="http://camunda.org/schema/1.0/dmn"
             id="Definitions_ID"
             name="Nome da Decisao"
             namespace="http://camunda.org/schema/1.0/dmn">
```

**Namespace INCORRETO (DMN 1.3 - NÃO USAR):**
```xml
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/">
```

### Hit Policy

Define como a tabela trata múltiplas regras que correspondem aos inputs:

| Hit Policy | Descrição | Uso |
|------------|-----------|-----|
| FIRST (F) | Retorna primeira regra que match | Mais comum - ordem importa |
| UNIQUE (U) | Apenas uma regra pode match | Regras mutuamente exclusivas |
| ANY (A) | Qualquer match (todas devem retornar mesmo valor) | Validação |
| COLLECT (C) | Retorna todos os matches em lista | Agregação |
| RULE ORDER (R) | Retorna todos na ordem das regras | Priorização |

**Recomendado:** Use `FIRST` para roteamento/decisões simples.

### Tipos de Dados

| TypeRef | Descrição | Exemplo Input | Exemplo Output |
|---------|-----------|---------------|----------------|
| string | Texto | `"UNIMED"` | `"AUTOMATICA"` |
| integer | Número inteiro | `27` | `2` |
| long | Número longo | `264064` | `12345678` |
| double | Número decimal | `99.99` | `0.5` |
| boolean | Verdadeiro/Falso | `true` | `false` |
| date | Data | | |

**IMPORTANTE:** Strings nos inputs/outputs devem estar entre aspas duplas: `"valor"`

### Expressões de Input

| Expressão | Significado |
|-----------|-------------|
| `"UNIMED"` | Igual a "UNIMED" |
| `"27"` | Igual a "27" (string) |
| `not("MANUAL")` | Diferente de "MANUAL" |
| (vazio) | Qualquer valor (wildcard) |
| `"A","B","C"` | Um dos valores da lista |

### Estrutura XML do DMN

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20180521/MODEL/"
             xmlns:dmndi="https://www.omg.org/spec/DMN/20180521/DMNDI/"
             xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/"
             xmlns:camunda="http://camunda.org/schema/1.0/dmn"
             id="Definitions_ID"
             name="Nome da Decisao"
             namespace="http://camunda.org/schema/1.0/dmn"
             exporter="Camunda Modeler"
             exporterVersion="5.x.x">

  <decision id="Decision_ID" name="Nome da Decisao" camunda:historyTimeToLive="180">
    <decisionTable id="DecisionTable_ID" hitPolicy="FIRST">

      <!-- INPUTS -->
      <input id="Input_1" label="Label do Input" camunda:inputVariable="">
        <inputExpression id="InputExpression_1" typeRef="string">
          <text>nome_variavel_processo</text>
        </inputExpression>
      </input>

      <!-- OUTPUTS -->
      <output id="Output_1" label="Label do Output" name="nome_output" typeRef="string" />

      <!-- REGRAS -->
      <rule id="Rule_1">
        <description>Descrição da regra</description>
        <inputEntry id="Input_R1_1">
          <text>"VALOR"</text>
        </inputEntry>
        <outputEntry id="Output_R1_1">
          <text>"RESULTADO"</text>
        </outputEntry>
      </rule>

    </decisionTable>
  </decision>

  <!-- DIAGRAMA (opcional) -->
  <dmndi:DMNDI>
    <dmndi:DMNDiagram id="DMNDiagram_ID">
      <dmndi:DMNShape id="DMNShape_Decision" dmnElementRef="Decision_ID">
        <dc:Bounds height="80" width="180" x="150" y="80" />
      </dmndi:DMNShape>
    </dmndi:DMNDiagram>
  </dmndi:DMNDI>
</definitions>
```

## Problema Conhecido: Tipo de Variável

### Problema: DMN retornando resultado errado

**Cenário:**
- Processo envia `convenio_codigo` como Integer (27)
- DMN espera String (`"27"`)
- DMN não encontra match → vai para regra default

**Causa:** Incompatibilidade de tipos entre variável do processo e input do DMN.

**Solução 1:** Ajustar o DMN para aceitar o tipo correto
```xml
<inputExpression id="InputExpression_1" typeRef="integer">
  <text>convenio_codigo</text>
</inputExpression>

<inputEntry id="Input_R1">
  <text>27</text>  <!-- SEM aspas para integer -->
</inputEntry>
```

**Solução 2:** Ajustar o processo para enviar o tipo correto
```python
# ERRADO - envia Integer
"convenio_codigo": {"value": 27, "type": "Integer"}

# CORRETO - envia String
"convenio_codigo": {"value": "27", "type": "String"}
```

**Recomendação:** Use STRING para códigos de convênio, pois:
- Permite valores como "UNIMED", "27", "BRADESCO"
- Mais flexível para diferentes fontes de dados
- Evita problemas de conversão

## Exemplo Completo: DMN de Roteamento

```xml
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20180521/MODEL/"
             xmlns:dmndi="https://www.omg.org/spec/DMN/20180521/DMNDI/"
             xmlns:dc="http://www.omg.org/spec/DMN/20180521/DC/"
             xmlns:camunda="http://camunda.org/schema/1.0/dmn"
             id="Definitions_Roteamento"
             name="DMN - Roteamento Convenio"
             namespace="http://camunda.org/schema/1.0/dmn">

  <decision id="Decision_Roteamento_Convenio"
            name="Definir Roteamento por Convenio"
            camunda:historyTimeToLive="180">

    <decisionTable id="DecisionTable_Roteamento" hitPolicy="FIRST">

      <!-- INPUT 1: Código do Convênio -->
      <input id="Input_Convenio" label="Codigo Convenio">
        <inputExpression id="InputExpression_Convenio" typeRef="string">
          <text>convenio_codigo</text>
        </inputExpression>
      </input>

      <!-- INPUT 2: Tipo de Procedimento -->
      <input id="Input_Procedimento" label="Tipo Procedimento">
        <inputExpression id="InputExpression_Procedimento" typeRef="string">
          <text>tipo_procedimento</text>
        </inputExpression>
      </input>

      <!-- OUTPUTS -->
      <output id="Output_TipoAutorizacao" label="Tipo Autorizacao"
              name="tipo_autorizacao" typeRef="string" />
      <output id="Output_RequerOPME" label="Requer OPME"
              name="requer_opme" typeRef="boolean" />
      <output id="Output_Prioridade" label="Prioridade"
              name="prioridade" typeRef="string" />
      <output id="Output_TopicoRPA" label="Topico RPA"
              name="topico_rpa" typeRef="string" />

      <!-- REGRA 1: Convênio código 27 -->
      <rule id="Rule_Convenio_27">
        <description>Convenio codigo 27 - Autorização automática via RPA</description>
        <inputEntry id="Input_R1_Convenio">
          <text>"27"</text>
        </inputEntry>
        <inputEntry id="Input_R1_Procedimento">
          <text></text>  <!-- Qualquer procedimento -->
        </inputEntry>
        <outputEntry id="Output_R1_Tipo">
          <text>"AUTOMATICA"</text>
        </outputEntry>
        <outputEntry id="Output_R1_OPME">
          <text>true</text>
        </outputEntry>
        <outputEntry id="Output_R1_Prioridade">
          <text>"MEDIA"</text>
        </outputEntry>
        <outputEntry id="Output_R1_Topico">
          <text>"ibm-rpa-autorizacao"</text>
        </outputEntry>
      </rule>

      <!-- REGRA 2: UNIMED Eletiva -->
      <rule id="Rule_Unimed_Eletiva">
        <description>Unimed com cirurgia eletiva usa RPA automatizado</description>
        <inputEntry id="Input_R2_Convenio">
          <text>"UNIMED"</text>
        </inputEntry>
        <inputEntry id="Input_R2_Procedimento">
          <text>"CIRURGIA_ELETIVA"</text>
        </inputEntry>
        <outputEntry id="Output_R2_Tipo">
          <text>"AUTOMATICA"</text>
        </outputEntry>
        <outputEntry id="Output_R2_OPME">
          <text>true</text>
        </outputEntry>
        <outputEntry id="Output_R2_Prioridade">
          <text>"MEDIA"</text>
        </outputEntry>
        <outputEntry id="Output_R2_Topico">
          <text>"ibm-rpa-unimed"</text>
        </outputEntry>
      </rule>

      <!-- REGRA 3: UNIMED Urgência -->
      <rule id="Rule_Unimed_Urgencia">
        <description>Unimed com urgencia requer atencao manual</description>
        <inputEntry id="Input_R3_Convenio">
          <text>"UNIMED"</text>
        </inputEntry>
        <inputEntry id="Input_R3_Procedimento">
          <text>"CIRURGIA_URGENCIA"</text>
        </inputEntry>
        <outputEntry id="Output_R3_Tipo">
          <text>"MANUAL"</text>
        </outputEntry>
        <outputEntry id="Output_R3_OPME">
          <text>true</text>
        </outputEntry>
        <outputEntry id="Output_R3_Prioridade">
          <text>"ALTA"</text>
        </outputEntry>
        <outputEntry id="Output_R3_Topico">
          <text></text>
        </outputEntry>
      </rule>

      <!-- REGRA DEFAULT: Outros convênios -->
      <rule id="Rule_Default">
        <description>Convenios nao mapeados vao para processo manual</description>
        <inputEntry id="Input_RD_Convenio">
          <text></text>  <!-- Qualquer valor -->
        </inputEntry>
        <inputEntry id="Input_RD_Procedimento">
          <text></text>  <!-- Qualquer valor -->
        </inputEntry>
        <outputEntry id="Output_RD_Tipo">
          <text>"MANUAL"</text>
        </outputEntry>
        <outputEntry id="Output_RD_OPME">
          <text>true</text>
        </outputEntry>
        <outputEntry id="Output_RD_Prioridade">
          <text>"MEDIA"</text>
        </outputEntry>
        <outputEntry id="Output_RD_Topico">
          <text></text>
        </outputEntry>
      </rule>

    </decisionTable>
  </decision>
</definitions>
```

## Integração com BPMN

### Chamar DMN do BPMN

No BPMN, use uma Business Rule Task:

```xml
<bpmn:businessRuleTask id="Task_DecidirRoteamento"
                       name="Decidir Roteamento"
                       camunda:resultVariable="decisaoRoteamento"
                       camunda:decisionRef="Decision_Roteamento_Convenio"
                       camunda:mapDecisionResult="singleResult">
  <bpmn:incoming>Flow_Anterior</bpmn:incoming>
  <bpmn:outgoing>Flow_Posterior</bpmn:outgoing>
</bpmn:businessRuleTask>
```

**Atributos importantes:**
- `camunda:decisionRef`: ID da decisão no DMN
- `camunda:resultVariable`: Nome da variável que receberá o resultado
- `camunda:mapDecisionResult`: Como mapear o resultado
  - `singleResult`: Retorna objeto com propriedades (ex: `decisaoRoteamento.tipo_autorizacao`)
  - `singleEntry`: Retorna valor único
  - `collectEntries`: Retorna lista

### Usar Output do DMN em Gateway

```xml
<bpmn:exclusiveGateway id="Gateway_TipoAutorizacao" name="Tipo de Autorizacao?">
  <bpmn:incoming>Flow_PosDecisao</bpmn:incoming>
  <bpmn:outgoing>Flow_Automatica</bpmn:outgoing>
  <bpmn:outgoing>Flow_Manual</bpmn:outgoing>
</bpmn:exclusiveGateway>

<bpmn:sequenceFlow id="Flow_Automatica"
                   sourceRef="Gateway_TipoAutorizacao"
                   targetRef="Task_RPA">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">
    ${tipo_autorizacao == 'AUTOMATICA'}
  </bpmn:conditionExpression>
</bpmn:sequenceFlow>

<bpmn:sequenceFlow id="Flow_Manual"
                   sourceRef="Gateway_TipoAutorizacao"
                   targetRef="Task_Manual">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">
    ${tipo_autorizacao == 'MANUAL'}
  </bpmn:conditionExpression>
</bpmn:sequenceFlow>
```

## Deploy do DMN

### Via REST API

```bash
curl -X POST "https://camunda.exemplo.com/engine-rest/deployment/create" \
  -F "deployment-name=dmn-roteamento" \
  -F "enable-duplicate-filtering=true" \
  -F "dmn=@dmn/Decision_Roteamento_Convenio.dmn"
```

### Via Python

```python
import requests

def deploy_dmn(camunda_url: str, dmn_file_path: str, deployment_name: str):
    endpoint = f"{camunda_url}/deployment/create"

    with open(dmn_file_path, 'rb') as f:
        files = {
            'deployment-name': (None, deployment_name),
            'enable-duplicate-filtering': (None, 'true'),
            'dmn': (dmn_file_path, f, 'application/xml')
        }
        response = requests.post(endpoint, files=files)
        response.raise_for_status()
        return response.json()
```

## Testar DMN via REST API

```bash
# Avaliar decisão diretamente
curl -X POST "https://camunda.exemplo.com/engine-rest/decision-definition/key/Decision_Roteamento_Convenio/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "convenio_codigo": {"value": "27", "type": "String"},
      "tipo_procedimento": {"value": "CIRURGIA_ELETIVA", "type": "String"}
    }
  }'
```

**Resposta esperada:**
```json
[
  {
    "tipo_autorizacao": {"value": "AUTOMATICA", "type": "String"},
    "requer_opme": {"value": true, "type": "Boolean"},
    "prioridade": {"value": "MEDIA", "type": "String"},
    "topico_rpa": {"value": "ibm-rpa-autorizacao", "type": "String"}
  }
]
```
```

---

## Checklist de Implementação

- [ ] Usar namespace DMN 1.1/1.2 (NÃO usar 20191111)
- [ ] Definir hitPolicy apropriado (FIRST recomendado)
- [ ] Tipos de variáveis consistentes (processo ↔ DMN)
- [ ] Strings entre aspas duplas nos inputs/outputs
- [ ] Regra default no final (catch-all)
- [ ] IDs únicos para cada elemento
- [ ] `camunda:historyTimeToLive` definido na decisão
- [ ] Testar deploy antes de usar no BPMN
- [ ] Testar avaliação via REST API

---

## Problemas Conhecidos e Soluções

### 1. ENGINE-09005 Could not parse DMN

**Erro:**
```
ENGINE-09005 Could not parse DMN: SAXException while parsing input
```

**Causa:** Namespace DMN 1.3 incompatível com Camunda 7.

**Solução:** Usar namespace `https://www.omg.org/spec/DMN/20180521/MODEL/`

---

### 2. DMN não encontra match (vai para default)

**Causa:** Tipo de variável incompatível.

**Diagnóstico:**
1. Verificar tipo da variável no processo (Integer vs String)
2. Verificar typeRef do input no DMN
3. Testar DMN via REST API com valores explícitos

**Solução:**
- Padronizar tipos (recomendado: usar String para códigos)
- Ajustar processo para enviar tipo correto
- Ajustar DMN para aceitar tipo recebido

---

### 3. Resultado do DMN não disponível no gateway

**Causa:** `camunda:mapDecisionResult` incorreto ou variável não mapeada.

**Solução:**
```xml
<!-- Use singleResult para acessar propriedades -->
<bpmn:businessRuleTask camunda:mapDecisionResult="singleResult"
                       camunda:resultVariable="resultado">
```

Acesso: `${resultado.tipo_autorizacao}`

---

### 4. Múltiplas regras correspondendo

**Causa:** Hit policy incorreto ou regras ambíguas.

**Solução:**
- Use `hitPolicy="FIRST"` e ordene regras da mais específica para mais genérica
- Regra default sempre no final

---

## Boas Práticas

1. **Nomes descritivos**: Use IDs e labels claros
2. **Documentação**: Adicione `<description>` em cada regra
3. **Ordem das regras**: Mais específicas primeiro, default por último
4. **Tipos consistentes**: Padronize tipos entre processo e DMN
5. **Versionamento**: Use deploy com duplicate filtering
6. **Testes**: Sempre teste via REST API antes de integrar

---

## Referências

- [Camunda DMN Reference](https://docs.camunda.org/manual/7.21/reference/dmn/)
- [DMN 1.1 Specification](https://www.omg.org/spec/DMN/1.1/)
- [Camunda REST API - Decision](https://docs.camunda.org/manual/7.21/reference/rest/decision-definition/)
