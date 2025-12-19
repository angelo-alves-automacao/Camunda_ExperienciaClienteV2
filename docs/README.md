# MVP - Autorização Cirúrgica com Camunda 7

---

## PROMPT IDEAL PARA PROJETOS CAMUNDA-FIRST

**Copie e cole este prompt no inicio de cada conversa para novos projetos de automacao:**

```
Voce e um arquiteto de solucoes especializado em Camunda 7 e automacao de processos.

PRINCIPIO FUNDAMENTAL: CAMUNDA-FIRST
=====================================
O Camunda e o ORQUESTRADOR. Toda logica de negocio, decisoes e fluxos
devem estar no BPMN e DMN, NUNCA no codigo dos workers.

REGRAS INVIOLAVEIS:
1. BPMN define QUAL tarefa executar e QUANDO
2. DMN define QUAL decisao tomar baseado em regras de negocio
3. Workers sao BURROS - apenas executam acoes tecnicas
4. Workers NUNCA decidem caminhos do processo
5. Workers NUNCA contem regras de negocio
6. Workers apenas RETORNAM dados tecnicos para o Camunda decidir

ARQUITETURA DE WORKERS:
- INPUT: Recebe variaveis do processo (ja decididas pelo BPMN/DMN)
- PROCESSO: Executa acao tecnica (API call, query, RPA)
- OUTPUT: Retorna resultados tecnicos puros
- ERRO: Retorna falha tecnica (Camunda trata via boundary events)

ANTI-PATTERNS A EVITAR:
- if/else no worker para decidir fluxo
- Validacoes de negocio no worker
- Worker chamando outro worker
- Logica condicional baseada em regras de negocio
- Hardcode de valores que deveriam estar no DMN

ESTRUTURA DO PROJETO:
camunda-projeto/
├── bpmn/           # Fluxos BPMN (orquestracao)
├── dmn/            # Tabelas de decisao (regras)
├── workers/        # External Tasks (integracoes tecnicas)
├── tests/          # Testes de integracao
├── .env            # Variaveis de ambiente
└── requirements.txt

PADRAO DE WORKER PYTHON:
def handle_task(task: ExternalTask) -> TaskResult:
    # 1. Recebe variaveis (ja decididas pelo BPMN/DMN)
    variables = task.get_variables()

    # 2. Executa acao TECNICA (sem decisoes de negocio)
    resultado = executar_acao_tecnica(variables)

    # 3. Retorna dados TECNICOS (Camunda decide o proximo passo)
    return TaskResult.success(task, {
        "status": resultado.status,
        "dados": resultado.dados
    })

INTEGRACAO IBM RPA (Process Management API):
- Autenticacao: POST /v1.0/token (OAuth username/password)
- Execucao: POST /v2.0/workspace/{workspaceId}/process/{processId}/instance
- Monitoramento: GET /v2.0/workspace/{workspaceId}/process/{processId}/instance/{instanceId}
- Status: NEW -> PROCESSING -> DONE/FAILED
- Header OBRIGATORIO: User-Agent (evita 403 do Azure Gateway)

PROBLEMA CONHECIDO - DMN VERSAO:
O Camunda 7 usa DMN 1.1/1.2. Se criar DMN com versao 1.3 (padrao do Modeler novo),
o deploy FALHA com erro de parsing. Sempre usar:
- namespace: https://www.omg.org/spec/DMN/20180521/MODEL/
- Camunda Modeler versao compativel com Camunda 7

Ao receber uma solicitacao de automacao:
1. Primeiro, desenhe o fluxo BPMN
2. Identifique decisoes -> crie tabelas DMN (versao 1.1)
3. Identifique integracoes -> crie External Tasks
4. Workers apenas executam, NUNCA decidem
```

---

## Visao Geral

Este projeto MVP valida a arquitetura de automacao baseada em **Camunda 7** com:

- **BPMN**: Orquestracao do fluxo de autorizacao cirurgica
- **DMN**: Decisao de roteamento por convenio
- **External Tasks**: Integracoes tecnicas (API Bus Austa e IBM RPA)

---

## DOCUMENTACAO DETALHADA (PROMPTS)

### Prompt Principal (Use em novos projetos)

| Prompt | Descricao |
|--------|-----------|
| **[PROMPT_CAMUNDA_MASTER.md](PROMPT_CAMUNDA_MASTER.md)** | **Prompt base Camunda-First - USE ESTE PRIMEIRO** |

### Prompts de Integracao (Referenciados pelo Master)

| Prompt | Descricao |
|--------|-----------|
| [PROMPT_CAMUNDA_DMN.md](PROMPT_CAMUNDA_DMN.md) | DMN - Tabelas de decisao, versoes, troubleshooting |
| [PROMPT_IBM_RPA_INTEGRATION.md](PROMPT_IBM_RPA_INTEGRATION.md) | IBM RPA - Process Management API |
| [PROMPT_ORACLE_AUTORIZACAO.md](PROMPT_ORACLE_AUTORIZACAO.md) | Oracle Tasy - Procedures de autorizacao |
| [PROMPT_ORACLE_NOTIFICACAO_WHATSAPP.md](PROMPT_ORACLE_NOTIFICACAO_WHATSAPP.md) | Oracle Tasy - Notificacao WhatsApp |

---

## PROBLEMAS CONHECIDOS E SOLUCOES

### 1. Erro de Deploy do DMN - Versao Incompativel

> **Documentacao completa:** [PROMPT_CAMUNDA_DMN.md](PROMPT_CAMUNDA_DMN.md)

**Erro:** `ENGINE-09005 Could not parse DMN: SAXException while parsing input`

**Solucao:** Usar namespace DMN 1.1: `https://www.omg.org/spec/DMN/20180521/MODEL/`

### 2. Erro 403 na API IBM RPA

> **Documentacao completa:** [PROMPT_IBM_RPA_INTEGRATION.md](PROMPT_IBM_RPA_INTEGRATION.md)

**Erro:** `403 Forbidden` ao chamar qualquer endpoint da API IBM RPA.

**Solucao:** Incluir header `User-Agent: IBM-RPA-Worker/1.0`

### 3. Erro "No metadata found for parameter" no IBM RPA

**Erro:** `400 Bad Request - No metadata found for parameter 'nome_param'`

**Solucao:** Definir Input Parameters no IBM RPA Studio com nomes EXATOS do payload.

### 4. Erro Oracle DPY-3015 password verifier

> **Documentacao completa:** [PROMPT_ORACLE_AUTORIZACAO.md](PROMPT_ORACLE_AUTORIZACAO.md)

**Erro:** `DPY-3015 password verifier type not supported`

**Solucao:** Usar modo thick do oracledb com Oracle Instant Client.

---

## Principios Arquiteturais

```
+------------------------------------------------------------------+
|                        CAMUNDA ENGINE                             |
+------------------------------------------------------------------+
|  BPMN: Define QUAL tarefa executar e QUANDO                      |
|  DMN:  Define QUAL decisao tomar baseado em regras               |
+------------------------------------------------------------------+
|                    EXTERNAL TASK WORKERS                          |
|  - NAO contem regras de negocio                                  |
|  - NAO decidem caminhos do processo                              |
|  - APENAS executam acoes tecnicas                                |
|  - APENAS retornam resultados tecnicos                           |
+------------------------------------------------------------------+
```

---

## Estrutura do Projeto

```
Camunda/
├── bpmn/
│   └── MVP_Autorizacao_Cirurgica.bpmn    # Fluxo BPMN
├── dmn/
│   └── Decision_Roteamento_Convenio.dmn  # Tabela de decisao (DMN 1.1)
├── workers/
│   ├── worker_api_consulta_paciente.py   # Consulta paciente via API
│   └── worker_ibm_rpa_autorizacao.py     # Executa RPA IBM
├── tests/
│   └── test_ibm_rpa_auth.py              # Teste de integracao IBM RPA
├── docs/
│   └── README.md                         # Esta documentacao
├── .env                                  # Variaveis de ambiente
└── requirements.txt                      # Dependencias Python
```

---

## Configuracao do Ambiente

### Arquivo .env

```env
# =============================================================================
# Configuracao do Ambiente - MVP Autorizacao Cirurgica
# =============================================================================

# CAMUNDA
CAMUNDA_URL=https://00000.austa.com.br/engine-rest

# API PACIENTE (Bus Austa)
API_PACIENTE_URL=https://0000.austaclinicas.com.br/api/autorizacao/cirurgia
API_TIMEOUT_SECONDS=30

# ORACLE / TASY
ORACLE_HOST=0000
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=0000
ORACLE_USER=0000
ORACLE_PASSWORD=0000

# IBM RPA (Process Management API)
IBM_RPA_API_URL=https://br1api.rpa.ibm.com
IBM_RPA_WORKSPACE_ID=0000
IBM_RPA_TENANT_ID=90000
IBM_RPA_USERNAME=robo.rpa@austa.com.br
IBM_RPA_PASSWORD=0000
IBM_RPA_PROCESS_ID=0000
IBM_RPA_TIMEOUT_SECONDS=300
IBM_RPA_POLL_INTERVAL_SECONDS=10

# WORKERS
WORKER_MAX_TASKS=1
WORKER_LOCK_DURATION=30000
WORKER_SLEEP_SECONDS=5
```

### Instalacao

```bash
# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

---

## Integracao IBM RPA - Process Management API

### Fluxo de Integracao

```
+-------------------+     +-------------------+     +-------------------+
|  1. Autenticacao  |---->|  2. Iniciar       |---->|  3. Monitorar     |
|  POST /v1.0/token |     |  POST /instance   |     |  GET /instance/id |
+-------------------+     +-------------------+     +-------------------+
        |                         |                         |
        v                         v                         v
   access_token              instance_id              status: DONE
```

### Endpoints

#### 1. Autenticacao (OAuth)

```
POST https://br1api.rpa.ibm.com/v1.0/token

Headers:
  tenantId: {tenant_id}
  Content-Type: application/x-www-form-urlencoded
  User-Agent: IBM-RPA-Worker/1.0    # OBRIGATORIO!
  Accept: */*

Body:
  grant_type=password&username={user}&password={pass}&culture=en-US

Response:
  { "access_token": "...", "expires_in": 3600 }
```

#### 2. Iniciar Processo

```
POST https://br1api.rpa.ibm.com/v2.0/workspace/{workspaceId}/process/{processId}/instance

Headers:
  Authorization: Bearer {access_token}
  Content-Type: application/json
  User-Agent: IBM-RPA-Worker/1.0
  Accept: application/json

Body:
  {
    "payload": {
      "paciente_nome": "Nome do Paciente",
      "convenio_codigo": 27,
      "procedimento_codigo": 10101020,
      "medico_crm": 1234,
      "guia_solicitacao": 1111
    }
  }

Response:
  { "id": "uuid-da-instancia" }
```

#### 3. Monitorar Execucao

```
GET https://br1api.rpa.ibm.com/v2.0/workspace/{workspaceId}/process/{processId}/instance/{instanceId}

Headers:
  Authorization: Bearer {access_token}
  User-Agent: IBM-RPA-Worker/1.0

Response:
  {
    "status": "done",
    "variables": [...],
    "outputs": { "status_execucao": 0.55 }
  }
```

### Status do Processo IBM RPA

| Status | Descricao | Acao |
|--------|-----------|------|
| NEW | Recem criado | Aguardar |
| QUEUED | Na fila | Aguardar |
| PROCESSING | Em execucao | Aguardar |
| DONE | Sucesso | Retornar SUCESSO |
| COMPLETED | Sucesso | Retornar SUCESSO |
| FAILED | Falhou | Retornar ERRO |
| CANCELED | Cancelado | Retornar ERRO |

---

## External Tasks (Workers Python)

### 1. oracle-consulta-paciente

**Topico Camunda**: `oracle-consulta-paciente`

Consulta dados do paciente via API Bus Austa.

| INPUT | OUTPUT |
|-------|--------|
| cpf_paciente | paciente_encontrado (boolean) |
| convenio_codigo | paciente_id |
| | paciente_nome |
| | convenio_codigo |
| | plano_ativo |
| | paciente_telefone |

### 2. ibm-rpa-autorizacao

**Topico Camunda**: `ibm-rpa-autorizacao`

Executa automacao IBM RPA e aguarda conclusao.

| INPUT | OUTPUT |
|-------|--------|
| paciente_nome | rpa_status (SUCESSO/ERRO/TIMEOUT) |
| convenio_codigo | rpa_instance_id |
| procedimento_codigo | rpa_mensagem |
| medico_crm | rpa_data_execucao |
| guia_solicitacao | numero_autorizacao |

**Fluxo do Worker:**
1. Inicia processo IBM RPA via API
2. Faz polling a cada 10s para verificar status
3. Quando status = DONE, retorna SUCESSO
4. Quando status = FAILED, retorna ERRO
5. Timeout de 300s se nao concluir

---

## Deploy no Camunda

### Via REST API

```bash
# Deploy BPMN e DMN
curl -X POST "https://camundahml.austa.com.br/engine-rest/deployment/create" \
  -F "deployment-name=mvp-autorizacao" \
  -F "enable-duplicate-filtering=true" \
  -F "bpmn=@bpmn/MVP_Autorizacao_Cirurgica.bpmn" \
  -F "dmn=@dmn/Decision_Roteamento_Convenio.dmn"
```

### Iniciar Processo (Teste)

```bash
curl -X POST "https://camundahml.austa.com.br/engine-rest/process-definition/key/Process_MVP_Autorizacao/start" \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "cpf_paciente": {"value": "22939549869", "type": "String"},
      "convenio_codigo": {"value": "UNIMED", "type": "String"},
      "tipo_procedimento": {"value": "CIRURGIA_ELETIVA", "type": "String"},
      "procedimento_codigo": {"value": "10101020", "type": "String"},
      "medico_crm": {"value": "1234", "type": "String"},
      "guia_solicitacao": {"value": "1111", "type": "String"}
    }
  }'
```

---

## Executar Workers

```bash
# Terminal 1: Worker consulta paciente
python workers/worker_api_consulta_paciente.py

# Terminal 2: Worker IBM RPA
python workers/worker_ibm_rpa_autorizacao.py
```

---

## Testes

### Teste de Integracao IBM RPA

```bash
python tests/test_ibm_rpa_auth.py
```

Saida esperada:
```
============================================================
TESTE IBM RPA - PROCESS MANAGEMENT API
============================================================
[1] Obtendo Access Token...
    Status: 200
    SUCESSO! Token obtido.

[2] Iniciando Processo IBM RPA...
    Status: 200
    SUCESSO! Processo iniciado.
    Instance ID: uuid-da-instancia

[3] Monitorando execucao do processo...
    Tentativa 1: Status = NEW
    Tentativa 2: Status = PROCESSING
    Tentativa 3: Status = DONE
    SUCESSO! Processo finalizado com status: DONE
============================================================
```

---

## Checklist de Validacao

### BPMN
- [x] Processo faz deploy sem erros
- [x] Gateways com condicoes corretas
- [x] External Tasks com topics corretos
- [x] Boundary event de timeout configurado

### DMN
- [x] Usando versao DMN 1.1 (compativel com Camunda 7)
- [x] Tabela carrega sem erros
- [x] Hit policy FIRST funciona
- [x] Outputs mapeados corretamente

### Workers
- [x] Conectam no Camunda
- [x] Subscrevem nos topics corretos
- [x] Worker API Paciente funcionando
- [x] Worker IBM RPA funcionando
- [x] Monitoramento de status funcionando
- [x] Retornam variaveis corretas

### IBM RPA
- [x] Header User-Agent incluido (evita 403)
- [x] Autenticacao OAuth funcionando
- [x] Inicio de processo funcionando
- [x] Envio de parametros funcionando
- [x] Monitoramento de status funcionando
- [x] Status DONE reconhecido como sucesso

---

## O que os Workers NAO fazem

- Nao decidem qual caminho seguir
- Nao validam elegibilidade
- Nao interpretam regras de negocio
- Nao controlam o fluxo

## O que os Workers FAZEM

- Executam chamadas de API
- Iniciam processos RPA
- Monitoram execucao
- Retornam resultados tecnicos
