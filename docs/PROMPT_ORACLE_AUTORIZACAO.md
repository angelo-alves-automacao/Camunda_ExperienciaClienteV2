# Prompt: Integração Camunda + Oracle Tasy - Atualização de Autorizações

Este documento contém o prompt padrão para criar workers de integração entre Camunda 7 e Oracle/Tasy para atualização de autorizações.

---

## Prompt para Geração de Worker Oracle Autorizações

```
Crie um External Task Worker Python para integração Camunda 7 + Oracle Tasy.

## Contexto Técnico

### Procedures Oracle para Atualização de Autorizações

**Procedure 1: Atualizar Dados da Guia**
```sql
CALL TASY.RPA_ATUALIZA_AUTORIZACAO_CONV(
    p_nr_sequencia,         -- Número sequencial da autorização
    p_nm_usuario,           -- 'automacaotasy'
    p_cd_senha,             -- Código da guia (nr_guia_requisicao)
    p_cd_autorizacao_prest, -- Código autorização prestador (nr_guia_requisicao)
    p_cd_autorizacao,       -- Código autorização (nr_guia_requisicao)
    p_dt_validade_guia      -- Data de validade (SYSDATE + 1)
);
```

**Procedure 2: Atualizar Estágio da Autorização**
```sql
CALL TASY.ATUALIZAR_AUTORIZACAO_CONVENIO(
    p_nr_sequencia,         -- Número sequencial (BPM_AUTORIZACOES_V.NR_SEQUENCIA)
    p_nm_usuario,           -- 'automacaotasy'
    p_nr_seq_estagio,       -- Código do estágio (ver mapeamento abaixo)
    p_ie_conta_particular,  -- 'N'
    p_ie_conta_convenio,    -- 'N'
    p_ie_commit             -- 'S'
);
```

### Mapeamento de Status para Estágio

O status de autorização retornado pelo RPA deve ser mapeado para o código de estágio do Tasy:

| Status RPA | Variações Aceitas | Estágio Tasy | Descrição |
|------------|-------------------|--------------|-----------|
| Autorizado | AUTORIZADO, Aprovado, APROVADO | 2 | Aprovado |
| Analise | ANALISE | 6 | Em Análise |
| Auditoria | AUDITORIA | 29 | Auditoria Médica |
| Negado | NEGADO, Recusado, RECUSADO | 7 | Negado |

**Código de mapeamento:**
```python
STATUS_PARA_ESTAGIO = {
    "Autorizado": 2,
    "AUTORIZADO": 2,
    "Aprovado": 2,
    "APROVADO": 2,
    "Analise": 6,
    "ANALISE": 6,
    "Auditoria": 29,
    "AUDITORIA": 29,
    "Negado": 7,
    "NEGADO": 7,
    "Recusado": 7,
    "RECUSADO": 7,
}

def obter_estagio_por_status(status_autorizacao: str) -> int:
    """
    Converte status_autorizacao para nr_seq_estagio do Tasy.
    Default: 6 (Análise) se status desconhecido.
    """
    if not status_autorizacao:
        return 6
    return STATUS_PARA_ESTAGIO.get(status_autorizacao.strip(), 6)
```

### Configuração Oracle Client (Modo Thick)

O Oracle Tasy usa autenticação legada que requer modo thick do oracledb:

```python
import oracledb
import os

# Caminho do Oracle Instant Client
ORACLE_CLIENT_PATH = os.getenv("ORACLE_CLIENT_PATH", r"C:\oracle_client\instantclient_23_8")

try:
    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_PATH)
except Exception as e:
    logging.warning(f"Oracle Client não inicializado: {e}")
```

## Variáveis de Ambiente (.env)

```env
# Camunda
CAMUNDA_URL=https://camunda.exemplo.com/engine-rest

# Oracle Tasy
ORACLE_HOST=servidor-oracle
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=TASY
ORACLE_USER=usuario_tasy
ORACLE_PASSWORD=senha_tasy

# Oracle Client (modo thick)
ORACLE_CLIENT_PATH=C:\oracle_client\instantclient_23_8
```

## Estrutura do Worker

```python
# 1. Configuração via dataclass
@dataclass
class OracleConfig:
    host: str
    port: int
    service_name: str
    user: str
    password: str

# 2. Repositório Oracle
class OracleAutorizacaoRepository:
    def _get_connection(self)
    def atualizar_autorizacao_guia(self, nr_sequencia, nr_guia_requisicao) -> dict
    def atualizar_estagio_autorizacao(self, nr_sequencia, status_autorizacao) -> dict
    def close(self)

# 3. Handler do External Task
def handle_atualizar_autorizacao(task: ExternalTask) -> TaskResult:
    # Recebe variáveis do Camunda
    # Chama procedures Oracle
    # Retorna TaskResult.success() com resultado

# 4. Worker principal
def main():
    worker = ExternalTaskWorker(...)
    worker.subscribe(topic_names="...", action=handle_atualizar_autorizacao)
```

## Input do Worker (Variáveis Camunda)

| Variável | Tipo | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| nr_sequencia | Integer | Sim | Número sequencial da autorização no Tasy |
| nr_guia_requisicao | String | Não | Número da guia retornado pelo RPA |
| status_autorizacao | String | Não | Status retornado pelo RPA (Autorizado, Negado, Analise) |

**Importante:** O `nr_sequencia` deve ser informado ao iniciar o processo no Camunda.

## Output do Worker (Variáveis Camunda)

| Variável | Tipo | Descrição |
|----------|------|-----------|
| oracle_status | String | SUCESSO ou ERRO |
| oracle_mensagem | String | Descrição do resultado |
| nr_seq_estagio | Integer | Código do estágio atribuído no Tasy |

## Exemplo de Implementação do Handler

```python
def handle_atualizar_autorizacao(task: ExternalTask) -> TaskResult:
    variables = task.get_variables()

    # Parâmetros obrigatórios
    nr_sequencia = variables.get('nr_sequencia')

    # Parâmetros do RPA
    nr_guia_requisicao = variables.get('nr_guia_requisicao')
    status_autorizacao = variables.get('status_autorizacao')

    # Validação
    if not nr_sequencia:
        return TaskResult.failure(
            task,
            error_message="nr_sequencia é obrigatório",
            error_details="Informe nr_sequencia ao iniciar o processo",
            retries=0,
            retry_timeout=5000
        )

    repository = OracleAutorizacaoRepository(OracleConfig())

    try:
        resultado = {
            'oracle_status': 'SUCESSO',
            'oracle_mensagem': '',
            'nr_seq_estagio': None
        }
        mensagens = []

        # 1. Atualiza dados da guia
        if nr_guia_requisicao:
            res = repository.atualizar_autorizacao_guia(
                nr_sequencia=int(nr_sequencia),
                nr_guia_requisicao=str(nr_guia_requisicao)
            )
            if res['procedure_guia_status'] == 'ERRO':
                resultado['oracle_status'] = 'ERRO'
            mensagens.append(f"Guia: {res['procedure_guia_status']}")

        # 2. Atualiza estágio
        if status_autorizacao:
            res = repository.atualizar_estagio_autorizacao(
                nr_sequencia=int(nr_sequencia),
                status_autorizacao=status_autorizacao
            )
            if res['procedure_estagio_status'] == 'ERRO':
                resultado['oracle_status'] = 'ERRO'
            resultado['nr_seq_estagio'] = res.get('nr_seq_estagio')
            mensagens.append(f"Estágio: {res.get('nr_seq_estagio')}")

        resultado['oracle_mensagem'] = ' | '.join(mensagens)
        return TaskResult.success(task, resultado)

    finally:
        repository.close()
```

## Exemplo de Chamada das Procedures

```python
def atualizar_autorizacao_guia(self, nr_sequencia: int, nr_guia_requisicao: str) -> dict:
    call_sql = """
        BEGIN
            TASY.RPA_ATUALIZA_AUTORIZACAO_CONV(
                :p_nr_sequencia,
                :p_nm_usuario,
                :p_cd_senha,
                :p_cd_autorizacao_prest,
                :p_cd_autorizacao,
                :p_dt_validade_guia
            );
        END;
    """

    cursor.execute(call_sql, {
        'p_nr_sequencia': nr_sequencia,
        'p_nm_usuario': 'automacaotasy',
        'p_cd_senha': nr_guia_requisicao,
        'p_cd_autorizacao_prest': nr_guia_requisicao,
        'p_cd_autorizacao': nr_guia_requisicao,
        'p_dt_validade_guia': datetime.now() + timedelta(days=1)
    })
    conn.commit()


def atualizar_estagio_autorizacao(self, nr_sequencia: int, status_autorizacao: str) -> dict:
    nr_seq_estagio = obter_estagio_por_status(status_autorizacao)

    call_sql = """
        BEGIN
            TASY.ATUALIZAR_AUTORIZACAO_CONVENIO(
                :p_nr_sequencia,
                :p_nm_usuario,
                :p_nr_seq_estagio,
                :p_ie_conta_particular,
                :p_ie_conta_convenio,
                :p_ie_commit
            );
        END;
    """

    cursor.execute(call_sql, {
        'p_nr_sequencia': nr_sequencia,
        'p_nm_usuario': 'automacaotasy',
        'p_nr_seq_estagio': nr_seq_estagio,
        'p_ie_conta_particular': 'N',
        'p_ie_conta_convenio': 'N',
        'p_ie_commit': 'S'
    })
    conn.commit()
```

## Dependências

```
camunda-external-task-client-python3>=4.0.0
oracledb>=2.0.0
python-dotenv>=1.0.0
```

**Requisito adicional:** Oracle Instant Client instalado no sistema.

## Topic Name

O worker deve se inscrever no tópico definido no BPMN:
- Exemplo: "oracle-registrar-autorizacao"
- Configurar no Service Task do BPMN: camunda:topic="oracle-registrar-autorizacao"
```

---

## Fluxo de Dados

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Processo      │     │   Worker Oracle  │     │    Oracle Tasy      │
│   Camunda       │────▶│   Autorizacao    │────▶│                     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                        │                         │
        │  nr_sequencia          │                         │
        │  nr_guia_requisicao    │  RPA_ATUALIZA_          │
        │  status_autorizacao    │  AUTORIZACAO_CONV       │
        │                        │─────────────────────────▶
        │                        │                         │
        │                        │  ATUALIZAR_AUTORIZACAO_ │
        │                        │  CONVENIO               │
        │                        │─────────────────────────▶
        │                        │                         │
        │  oracle_status         │                         │
        │  oracle_mensagem       │                         │
        │  nr_seq_estagio        │                         │
        ◀────────────────────────│                         │
```

---

## Checklist de Implementação

- [ ] Instalar Oracle Instant Client
- [ ] Configurar ORACLE_CLIENT_PATH no .env
- [ ] Configurar credenciais Oracle no .env
- [ ] Criar worker Python seguindo a estrutura acima
- [ ] Implementar mapeamento status → estágio
- [ ] Configurar topic name no BPMN (Service Task → External)
- [ ] Adicionar nr_sequencia como parâmetro de entrada do processo
- [ ] Testar procedures com dados reais
- [ ] Validar commits no banco Oracle

---

## Troubleshooting

### Erro: DPY-3015 password verifier type not supported

**Causa:** Oracle Client não está em modo thick.

**Solução:**
```python
oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_PATH)
```

### Erro: DPI-1047 Cannot locate Oracle Client library

**Causa:** Caminho do Oracle Instant Client incorreto.

**Solução:** Verificar se o caminho existe e contém os arquivos .dll/.so do Oracle Client.

### Erro: ORA-06550 PL/SQL compilation error

**Causa:** Nome da procedure ou parâmetros incorretos.

**Solução:** Verificar nomes exatos das procedures no banco Oracle.

---

## Referências

- [python-oracledb Documentation](https://python-oracledb.readthedocs.io/)
- [Oracle Instant Client Downloads](https://www.oracle.com/database/technologies/instant-client/downloads.html)
- [Camunda External Task Client Python](https://github.com/camunda-community-hub/camunda-external-task-client-python3)
