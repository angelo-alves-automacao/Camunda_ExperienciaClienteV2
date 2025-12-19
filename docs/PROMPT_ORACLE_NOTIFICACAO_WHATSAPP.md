# Prompt: Integração Camunda + Oracle Tasy - Notificação WhatsApp

Este documento contém o prompt padrão para criar workers de integração entre Camunda 7 e Oracle/Tasy para disparo de notificações via WhatsApp.

---

## Prompt para Geração de Worker Oracle Notificação WhatsApp

```
Crie um External Task Worker Python para integração Camunda 7 + Oracle Tasy para notificação WhatsApp.

## Contexto Técnico

### Tabela de Envios WhatsApp

A tabela `TASY.AUSTA_ENVIOS_WHATSAPP` possui um **trigger que dispara automaticamente** o envio da mensagem WhatsApp após o INSERT. O worker apenas insere o registro e o banco cuida do envio.

**Estrutura do INSERT:**
```sql
INSERT INTO TASY.AUSTA_ENVIOS_WHATSAPP (
    -- Campos de controle (valores fixos)
    CD_MODELO,           -- Código do template de mensagem
    DT_CRIACAO,          -- SYSDATE
    DT_ENVIO,            -- SYSDATE
    DS_PARAMETROS,       -- NULL
    CD_STATUS,           -- 0 (pendente)
    DS_MENSAGEM_ERRO,    -- NULL
    CD_STATUS_ENVIO,     -- 1 (aguardando envio)

    -- Campos de dados (dinâmicos)
    NR_TELEFONE,         -- Telefone do destinatário
    NR_SEQ_AUTORIZACAO,  -- Número sequencial da autorização
    DATA_AUTORIZACAO,    -- SYSDATE
    DATA_CONSULTA        -- SYSDATE
) VALUES (
    :cd_modelo,
    SYSDATE,
    SYSDATE,
    NULL,
    0,
    NULL,
    1,
    :nr_telefone,
    :nr_seq_autorizacao,
    SYSDATE,
    SYSDATE
);
```

### Mapeamento de Status para Modelo de Mensagem

O status de autorização retornado pelo RPA/processo deve ser mapeado para o código do template de mensagem:

| Status Autorização | Variações Aceitas | CD_MODELO | Descrição Template |
|--------------------|-------------------|-----------|-------------------|
| Autorizado | AUTORIZADO, Aprovado, APROVADO | 27 | Mensagem de aprovação |
| Negado | NEGADO, Recusado, RECUSADO | 3 | Mensagem de negação |

**Código de mapeamento:**
```python
STATUS_PARA_MODELO = {
    "Autorizado": 27,
    "AUTORIZADO": 27,
    "Aprovado": 27,
    "APROVADO": 27,
    "Negado": 3,
    "NEGADO": 3,
    "Recusado": 3,
    "RECUSADO": 3,
}

MODELO_DEFAULT = 27  # Default: template aprovado

def obter_modelo_por_status(status_autorizacao: str) -> int:
    """
    Converte status_autorizacao para CD_MODELO do WhatsApp.
    Default: 27 (aprovado) se status desconhecido.
    """
    if not status_autorizacao:
        return MODELO_DEFAULT
    return STATUS_PARA_MODELO.get(status_autorizacao.strip(), MODELO_DEFAULT)
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
class OracleNotificacaoRepository:
    def _get_connection(self)
    def inserir_notificacao_whatsapp(self, nr_sequencia, status_autorizacao, nr_telefone) -> dict
    def close(self)

# 3. Handler do External Task
def handle_notificar_medico(task: ExternalTask) -> TaskResult:
    # Recebe variáveis do Camunda
    # Determina CD_MODELO baseado no status
    # Insere registro na tabela
    # Retorna TaskResult.success() com resultado

# 4. Worker principal
def main():
    worker = ExternalTaskWorker(...)
    worker.subscribe(topic_names="...", action=handle_notificar_medico)
```

## Input do Worker (Variáveis Camunda)

| Variável | Tipo | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| nr_sequencia | Integer | Sim | Número sequencial da autorização no Tasy |
| status_autorizacao | String | Não | Status da autorização (Autorizado, Negado) |
| nr_telefone | String | Não | Telefone do destinatário (default se não informado) |

**Importante:** O `nr_sequencia` deve ser informado ao iniciar o processo no Camunda.

## Output do Worker (Variáveis Camunda)

| Variável | Tipo | Descrição |
|----------|------|-----------|
| notificacao_status | String | SUCESSO ou ERRO |
| notificacao_mensagem | String | Descrição do resultado |
| cd_modelo | Integer | Código do template de mensagem usado |

## Exemplo de Implementação do Handler

```python
def handle_notificar_medico(task: ExternalTask) -> TaskResult:
    variables = task.get_variables()

    # Parâmetros
    nr_sequencia = variables.get('nr_sequencia')
    status_autorizacao = variables.get('status_autorizacao')
    nr_telefone = variables.get('nr_telefone', '5517999999999')  # Default

    # Validação
    if not nr_sequencia:
        return TaskResult.failure(
            task,
            error_message="nr_sequencia é obrigatório",
            error_details="Informe nr_sequencia ao iniciar o processo",
            retries=0,
            retry_timeout=5000
        )

    repository = OracleNotificacaoRepository(OracleConfig())

    try:
        resultado = repository.inserir_notificacao_whatsapp(
            nr_sequencia=int(nr_sequencia),
            status_autorizacao=status_autorizacao,
            nr_telefone=str(nr_telefone)
        )

        return TaskResult.success(task, resultado)

    finally:
        repository.close()
```

## Exemplo de INSERT

```python
def inserir_notificacao_whatsapp(
    self,
    nr_sequencia: int,
    status_autorizacao: str,
    nr_telefone: str
) -> dict:
    """
    Insere registro na tabela AUSTA_ENVIOS_WHATSAPP.
    O trigger do banco dispara automaticamente o envio.
    """
    insert_sql = """
        INSERT INTO TASY.AUSTA_ENVIOS_WHATSAPP (
            CD_MODELO,
            DT_CRIACAO,
            DT_ENVIO,
            DS_PARAMETROS,
            CD_STATUS,
            DS_MENSAGEM_ERRO,
            CD_STATUS_ENVIO,
            NR_TELEFONE,
            NR_SEQ_AUTORIZACAO,
            DATA_AUTORIZACAO,
            DATA_CONSULTA
        ) VALUES (
            :cd_modelo,
            SYSDATE,
            SYSDATE,
            NULL,
            0,
            NULL,
            1,
            :nr_telefone,
            :nr_seq_autorizacao,
            SYSDATE,
            SYSDATE
        )
    """

    try:
        conn = self._get_connection()
        cursor = conn.cursor()

        # Determina o modelo baseado no status
        cd_modelo = obter_modelo_por_status(status_autorizacao)

        cursor.execute(insert_sql, {
            'cd_modelo': cd_modelo,
            'nr_telefone': nr_telefone,
            'nr_seq_autorizacao': nr_sequencia
        })

        conn.commit()

        return {
            'notificacao_status': 'SUCESSO',
            'notificacao_mensagem': f'Notificação inserida - modelo {cd_modelo}',
            'cd_modelo': cd_modelo
        }

    except Exception as e:
        if self._connection:
            self._connection.rollback()
        return {
            'notificacao_status': 'ERRO',
            'notificacao_mensagem': str(e),
            'cd_modelo': None
        }
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
- Exemplo: "oracle-notificacao-medico"
- Configurar no Service Task do BPMN: camunda:topic="oracle-notificacao-medico"
```

---

## Fluxo de Dados

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Processo      │     │   Worker Oracle  │     │    Oracle Tasy      │
│   Camunda       │────▶│   Notificacao    │────▶│                     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                        │                         │
        │  nr_sequencia          │                         │
        │  status_autorizacao    │  INSERT INTO            │
        │  nr_telefone           │  AUSTA_ENVIOS_WHATSAPP  │
        │                        │─────────────────────────▶
        │                        │                         │
        │                        │                    ┌────┴────┐
        │                        │                    │ TRIGGER │
        │                        │                    │ DISPARA │
        │                        │                    │ ENVIO   │
        │                        │                    └────┬────┘
        │                        │                         │
        │                        │                         ▼
        │                        │                   ┌───────────┐
        │                        │                   │ WhatsApp  │
        │                        │                   │ API       │
        │                        │                   └───────────┘
        │                        │                         │
        │  notificacao_status    │                         │
        │  notificacao_mensagem  │                         │
        │  cd_modelo             │                         │
        ◀────────────────────────│                         │
```

---

## Campos da Tabela AUSTA_ENVIOS_WHATSAPP

| Campo | Tipo | Valor | Descrição |
|-------|------|-------|-----------|
| CD_MODELO | NUMBER | 27 ou 3 | Código do template de mensagem |
| DT_CRIACAO | DATE | SYSDATE | Data de criação do registro |
| DT_ENVIO | DATE | SYSDATE | Data programada para envio |
| DS_PARAMETROS | VARCHAR2 | NULL | Parâmetros adicionais (não usado) |
| CD_STATUS | NUMBER | 0 | Status do registro (0=pendente) |
| DS_MENSAGEM_ERRO | VARCHAR2 | NULL | Mensagem de erro (se houver) |
| CD_STATUS_ENVIO | NUMBER | 1 | Status do envio (1=aguardando) |
| NR_TELEFONE | VARCHAR2 | Dinâmico | Telefone com DDD (ex: 5517999999999) |
| NR_SEQ_AUTORIZACAO | NUMBER | Dinâmico | nr_sequencia da autorização |
| DATA_AUTORIZACAO | DATE | SYSDATE | Data da autorização |
| DATA_CONSULTA | DATE | SYSDATE | Data da consulta |

---

## Templates de Mensagem (CD_MODELO)

| CD_MODELO | Tipo | Uso |
|-----------|------|-----|
| 27 | Aprovação | Autorização aprovada pelo convênio |
| 3 | Negação | Autorização negada pelo convênio |

**Nota:** Os templates são configurados no sistema Tasy. O CD_MODELO referencia qual template será usado para montar a mensagem.

---

## Checklist de Implementação

- [ ] Instalar Oracle Instant Client
- [ ] Configurar ORACLE_CLIENT_PATH no .env
- [ ] Configurar credenciais Oracle no .env
- [ ] Criar worker Python seguindo a estrutura acima
- [ ] Implementar mapeamento status → CD_MODELO
- [ ] Configurar topic name no BPMN (Service Task → External)
- [ ] Adicionar nr_sequencia como parâmetro de entrada do processo
- [ ] Testar INSERT com dados reais
- [ ] Validar trigger de disparo do WhatsApp

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

### Erro: ORA-00942 table or view does not exist

**Causa:** Tabela AUSTA_ENVIOS_WHATSAPP não existe ou usuário sem permissão.

**Solução:** Verificar permissões do usuário Oracle na tabela.

### Mensagem não enviada após INSERT

**Causa:** Trigger não está ativo ou falhou silenciosamente.

**Solução:**
1. Verificar se o trigger está habilitado
2. Consultar CD_STATUS e DS_MENSAGEM_ERRO na tabela
3. Verificar logs do sistema de envio WhatsApp

---

## Referências

- [python-oracledb Documentation](https://python-oracledb.readthedocs.io/)
- [Oracle Instant Client Downloads](https://www.oracle.com/database/technologies/instant-client/downloads.html)
- [Camunda External Task Client Python](https://github.com/camunda-community-hub/camunda-external-task-client-python3)
