# Prompt: Integração Camunda + IBM RPA

Este documento contém o prompt padrão para criar workers de integração entre Camunda 7 e IBM RPA Process Management API.

---

## Prompt para Geração de Worker IBM RPA

```
Crie um External Task Worker Python para integração Camunda 7 + IBM RPA.

## Contexto Técnico

### IBM RPA Process Management API v2.0

**Autenticação:**
- POST /v1.0/token
- Headers: tenantId, Content-Type: application/x-www-form-urlencoded
- Body: grant_type=password&username={user}&password={pass}&culture=en-US
- Retorna: { "access_token": "..." }

**Iniciar Processo:**
- POST /v2.0/workspace/{workspaceId}/process/{processId}/instance
- Headers: Authorization: Bearer {token}, Content-Type: application/json
- Body: { "payload": { ...variáveis de entrada... } }
- Retorna: { "id": "instance-uuid" }

**Consultar Status:**
- GET /v2.0/workspace/{workspaceId}/process/{processId}/instance/{instanceId}
- Retorna estrutura com status e outputs

### Estrutura de Retorno do IBM RPA (PADRÃO)

O status de execução é SEMPRE padronizado:
- "status": "done" | "failed" | "canceled" | "running" | "queued" | "new"

As variáveis de saída são DINÂMICAS e vêm em dois lugares:
```json
{
    "status": "done",
    "variables": [
        { "name": "var_entrada_1", "value": "..." },
        { "name": "var_entrada_2", "value": 123.0 }
    ],
    "outputs": {
        "variavel_saida_1": "valor_string",
        "variavel_saida_2": 456.0
    }
}
```

### Regras de Mapeamento de Outputs

1. **Status de execução** (fixo):
   - Mapear "done"/"completed" -> rpa_status = "SUCESSO"
   - Mapear "failed"/"canceled"/"error" -> rpa_status = "ERRO"
   - Mapear timeout -> rpa_status = "TIMEOUT"

2. **Variáveis de saída** (dinâmicas):
   - Extrair TODAS as chaves do objeto "outputs"
   - Converter tipos:
     - float com .0 -> int -> string (ex: 95687.0 -> "95687")
     - outros tipos -> manter ou converter para string
   - Inserir cada variável no processo Camunda

3. **Variáveis fixas do worker**:
   - rpa_status: String (SUCESSO, ERRO, TIMEOUT)
   - rpa_instance_id: String (UUID da instância)
   - rpa_mensagem: String (descrição do resultado)
   - rpa_data_execucao: String (ISO datetime)

## Variáveis de Ambiente (.env)

```env
# Camunda
CAMUNDA_URL=https://camunda.exemplo.com/engine-rest

# IBM RPA
IBM_RPA_API_URL=https://br1api.rpa.ibm.com
IBM_RPA_WORKSPACE_ID=seu-workspace-id
IBM_RPA_TENANT_ID=seu-tenant-id
IBM_RPA_USERNAME=usuario@email.com
IBM_RPA_PASSWORD=senha
IBM_RPA_PROCESS_ID=uuid-do-processo
IBM_RPA_TIMEOUT_SECONDS=300
IBM_RPA_POLL_INTERVAL_SECONDS=10
```

## Estrutura do Worker

```python
# 1. Configuração via dataclass
@dataclass
class IBMRPAConfig:
    api_url: str
    workspace_id: str
    tenant_id: str
    username: str
    password: str
    process_id: str
    timeout_seconds: int
    poll_interval_seconds: int

# 2. Cliente IBM RPA
class IBMRPAClient:
    def _obter_token(self) -> str
    def iniciar_processo(self, process_id, payload) -> str
    def consultar_status_instancia(self, process_id, instance_id) -> dict
    def aguardar_conclusao(self, process_id, instance_id) -> Tuple[str, str, dict]

# 3. Handler do External Task
def handle_task(task: ExternalTask) -> TaskResult:
    # Recebe variáveis do Camunda
    # Monta payload para IBM RPA
    # Inicia processo e aguarda conclusão
    # Mapeia outputs dinâmicos
    # Retorna TaskResult.success() com variáveis

# 4. Worker principal
def main():
    worker = ExternalTaskWorker(...)
    worker.subscribe(topic_names="...", action=handle_task)
```

## Mapeamento Dinâmico de Outputs

```python
def mapear_outputs_dinamicos(rpa_output: dict) -> dict:
    """
    Mapeia TODAS as variáveis de saída do IBM RPA para o Camunda.

    Args:
        rpa_output: Dict com 'outputs' e 'variables' do IBM RPA

    Returns:
        Dict com variáveis para inserir no processo Camunda
    """
    resultado = {}

    if not rpa_output or not isinstance(rpa_output, dict):
        return resultado

    outputs = rpa_output.get('outputs', {})

    # Mapeia cada chave do outputs
    for nome_var, valor in outputs.items():
        # Converte float inteiro para string (ex: 95687.0 -> "95687")
        if isinstance(valor, float) and valor.is_integer():
            resultado[nome_var] = str(int(valor))
        elif valor is not None:
            resultado[nome_var] = valor

    return resultado
```

## Exemplo de Uso no Handler

```python
def handle_executar_rpa(task: ExternalTask) -> TaskResult:
    variables = task.get_variables()

    # Monta payload com variáveis de entrada
    rpa_payload = {
        "cpf_paciente": variables.get('cpf_paciente'),
        "convenio_codigo": variables.get('convenio_codigo'),
        # ... outras variáveis de entrada
    }

    client = IBMRPAClient(config)

    try:
        # Inicia e aguarda
        instance_id = client.iniciar_processo(config.process_id, rpa_payload)
        rpa_status, rpa_mensagem, rpa_output = client.aguardar_conclusao(
            config.process_id, instance_id
        )

        # Variáveis fixas do worker
        resultado = {
            "rpa_status": rpa_status,
            "rpa_instance_id": instance_id,
            "rpa_mensagem": rpa_mensagem,
            "rpa_data_execucao": datetime.now().isoformat(),
        }

        # Adiciona outputs dinâmicos do script RPA
        outputs_dinamicos = mapear_outputs_dinamicos(rpa_output)
        resultado.update(outputs_dinamicos)

        return TaskResult.success(task, resultado)

    except Exception as e:
        return TaskResult.success(task, {
            "rpa_status": "ERRO",
            "rpa_instance_id": None,
            "rpa_mensagem": f"Erro técnico: {e}",
            "rpa_data_execucao": datetime.now().isoformat(),
        })
```

## Outputs Esperados no Processo Camunda

### Variáveis Fixas (sempre retornadas):
| Variável | Tipo | Descrição |
|----------|------|-----------|
| rpa_status | String | SUCESSO, ERRO ou TIMEOUT |
| rpa_instance_id | String | UUID da instância no IBM RPA |
| rpa_mensagem | String | Mensagem descritiva do resultado |
| rpa_data_execucao | String | Data/hora ISO da execução |

### Variáveis Dinâmicas (dependem do script RPA):
Todas as chaves presentes no objeto `outputs` do retorno do IBM RPA serão automaticamente inseridas no processo Camunda com o mesmo nome.

Exemplo - se o script RPA retornar:
```json
{
    "outputs": {
        "status_autorizacao": "Autorizado",
        "nr_guia_requisicao": 95687.0,
        "protocolo": "ABC123"
    }
}
```

O processo Camunda receberá:
- status_autorizacao = "Autorizado"
- nr_guia_requisicao = "95687"
- protocolo = "ABC123"

## Dependências

```
camunda-external-task-client-python3>=4.0.0
requests>=2.28.0
python-dotenv>=1.0.0
```

## Topic Name

O worker deve se inscrever no tópico definido no BPMN:
- Exemplo: "ibm-rpa-autorizacao"
- Configurar no Service Task do BPMN: camunda:topic="ibm-rpa-autorizacao"
```

---

## Checklist de Implementação

- [ ] Criar arquivo .env com credenciais IBM RPA
- [ ] Criar worker Python seguindo a estrutura acima
- [ ] Configurar topic name no BPMN (Service Task -> External)
- [ ] Implementar mapeamento dinâmico de outputs
- [ ] Tratar conversão de tipos (float -> int -> string)
- [ ] Adicionar logging para debug
- [ ] Testar com processo real no IBM RPA

---

## Referências

- [IBM RPA Process Management API](https://www.ibm.com/docs/en/rpa)
- [Camunda External Task Client Python](https://github.com/camunda-community-hub/camunda-external-task-client-python3)
- [Camunda 7 REST API](https://docs.camunda.org/manual/7.21/reference/rest/)
