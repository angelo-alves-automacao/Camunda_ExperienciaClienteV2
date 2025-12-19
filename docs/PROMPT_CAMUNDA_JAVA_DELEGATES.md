# Prompt: Integração BPMN + Java Delegates no Camunda 7

Este documento contém o prompt padrão para criar integrações funcionais entre BPMN e Java Delegates no Camunda 7.

---

## ⚠️ PROBLEMAS COMUNS QUE ESTE PROMPT RESOLVE

| Problema | Causa | Solução |
|----------|-------|---------|
| Timer sem ação | Boundary Event sem sequenceFlow de saída | Sempre conectar timer a uma tarefa/gateway |
| Delegate não executa | Configurado como External Task mas código é Delegate | Usar `camunda:class` ou `camunda:delegateExpression` |
| Variável não existe | BPMN espera variável que Delegate não cria | Documentar INPUT/OUTPUT de cada Delegate |
| Bean não encontrado | Spring não registrou o bean | Usar `@Component` e nome correto |
| Método não chamado | `${service.metodo}` mas classe espera variável | Padronizar invocação |

---

## Prompt para Geração de BPMN + Java Delegates

```
Você é um arquiteto especializado em Camunda 7 com Java/Spring Boot.

================================================================================
PRINCÍPIO: CONSISTÊNCIA BPMN ↔ CÓDIGO
================================================================================

Para cada tarefa no BPMN que executa código Java, você DEVE garantir:

1. A configuração no BPMN corresponde EXATAMENTE ao tipo de código
2. Todas as variáveis esperadas pelo código existem no processo
3. Todos os Boundary Events têm sequenceFlow de saída
4. Todos os Delegates estão registrados como beans Spring

================================================================================
TIPOS DE INVOCAÇÃO JAVA NO CAMUNDA 7
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ TIPO              │ CONFIGURAÇÃO BPMN           │ QUANDO USAR               │
├───────────────────┼─────────────────────────────┼───────────────────────────┤
│ Java Delegate     │ camunda:class="..."         │ Código síncrono interno   │
│                   │ camunda:delegateExpression  │ Com injeção de dependência│
├───────────────────┼─────────────────────────────┼───────────────────────────┤
│ External Task     │ camunda:type="external"     │ Workers externos (Python, │
│                   │ camunda:topic="..."         │ Node, microserviços)      │
├───────────────────┼─────────────────────────────┼───────────────────────────┤
│ Expression        │ camunda:expression="..."    │ Chamada direta a método   │
│                   │                             │ de bean Spring            │
└─────────────────────────────────────────────────────────────────────────────┘

⚠️ ERRO CRÍTICO: Misturar tipos!
   - Se BPMN tem camunda:type="external" → código DEVE ser Worker externo
   - Se código é JavaDelegate → BPMN DEVE ter camunda:class ou delegateExpression

================================================================================
PADRÃO 1: JAVA DELEGATE COM CLASSE DIRETA
================================================================================

**Uso:** Quando a classe não precisa de injeção de dependências.

**BPMN:**
```xml
<bpmn:serviceTask id="Task_Exemplo"
                  name="Executar Ação"
                  camunda:class="com.empresa.delegates.ExemploDelegate">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:serviceTask>
```

**Java:**
```java
package com.empresa.delegates;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ExemploDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ExemploDelegate.class);

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        logger.info("Executando ExemploDelegate - ProcessInstance: {}",
                    execution.getProcessInstanceId());

        // 1. LER variáveis do processo
        String cpfPaciente = (String) execution.getVariable("cpf_paciente");
        Integer convenio = (Integer) execution.getVariable("convenio_codigo");

        // 2. EXECUTAR lógica técnica
        String resultado = processarLogica(cpfPaciente, convenio);

        // 3. ESCREVER variáveis de saída
        execution.setVariable("resultado_processamento", resultado);
        execution.setVariable("status_delegate", "SUCESSO");

        logger.info("ExemploDelegate concluído - Resultado: {}", resultado);
    }

    private String processarLogica(String cpf, Integer convenio) {
        // Lógica de negócio aqui
        return "OK";
    }
}
```

================================================================================
PADRÃO 2: JAVA DELEGATE COM SPRING (RECOMENDADO)
================================================================================

**Uso:** Quando precisa de injeção de dependências (Repository, Service, etc).

**BPMN:**
```xml
<bpmn:serviceTask id="Task_ValidarGuia"
                  name="Validar Guia TISS"
                  camunda:delegateExpression="${validarGuiaDelegate}">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:serviceTask>
```

⚠️ **IMPORTANTE:** O nome do bean `${validarGuiaDelegate}` DEVE corresponder ao @Component!

**Java:**
```java
package com.empresa.delegates.tiss;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component("validarGuiaDelegate")  // ⚠️ NOME DEVE CORRESPONDER AO BPMN
public class ValidarGuiaDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ValidarGuiaDelegate.class);

    @Autowired
    private TissRepository tissRepository;

    @Autowired
    private GuiaService guiaService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String taskId = execution.getCurrentActivityId();
        String processId = execution.getProcessInstanceId();

        logger.info("[{}] Iniciando validação de guia - Process: {}", taskId, processId);

        try {
            // 1. LER variáveis de entrada
            String numeroGuia = getVariableAsString(execution, "numero_guia");
            String cpfBeneficiario = getVariableAsString(execution, "cpf_beneficiario");

            // 2. VALIDAR variáveis obrigatórias
            if (numeroGuia == null || numeroGuia.isEmpty()) {
                throw new IllegalArgumentException("numero_guia é obrigatório");
            }

            // 3. EXECUTAR lógica com dependências injetadas
            GuiaValidacao resultado = guiaService.validar(numeroGuia, cpfBeneficiario);

            // 4. ESCREVER variáveis de saída
            execution.setVariable("guia_valida", resultado.isValida());
            execution.setVariable("guia_mensagem", resultado.getMensagem());
            execution.setVariable("guia_codigo_retorno", resultado.getCodigo());

            logger.info("[{}] Validação concluída - Válida: {}", taskId, resultado.isValida());

        } catch (Exception e) {
            logger.error("[{}] Erro na validação: {}", taskId, e.getMessage(), e);
            execution.setVariable("guia_valida", false);
            execution.setVariable("guia_erro", e.getMessage());
            throw e; // Re-throw para Camunda tratar
        }
    }

    private String getVariableAsString(DelegateExecution execution, String name) {
        Object value = execution.getVariable(name);
        return value != null ? value.toString() : null;
    }
}
```

================================================================================
PADRÃO 3: SERVICE COM MÉTODO ESPECÍFICO (EXPRESSION)
================================================================================

**Uso:** Quando quer chamar método específico de um Service.

**BPMN:**
```xml
<bpmn:serviceTask id="Task_EnviarEmail"
                  name="Enviar Notificação"
                  camunda:expression="${notificacaoService.enviarEmail(execution)}">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>
</bpmn:serviceTask>
```

**Java:**
```java
package com.empresa.services;

import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.springframework.stereotype.Service;

@Service("notificacaoService")
public class NotificacaoService {

    public void enviarEmail(DelegateExecution execution) {
        String destinatario = (String) execution.getVariable("email_destinatario");
        String assunto = (String) execution.getVariable("email_assunto");
        String corpo = (String) execution.getVariable("email_corpo");

        // Lógica de envio
        boolean enviado = enviarEmailReal(destinatario, assunto, corpo);

        execution.setVariable("email_enviado", enviado);
    }

    public void enviarSms(DelegateExecution execution) {
        // Outro método do mesmo service
    }

    private boolean enviarEmailReal(String dest, String assunto, String corpo) {
        // Implementação real
        return true;
    }
}
```

⚠️ **ANTI-PATTERN:** Não use variável para decidir método!

```java
// ❌ ERRADO - Difícil de manter e debugar
@Service("tissService")
public class TissService {
    public void executar(DelegateExecution execution) {
        String metodo = (String) execution.getVariable("tissMethod");
        if ("validarGuia".equals(metodo)) {
            validarGuia(execution);
        } else if ("autorizarProcedimento".equals(metodo)) {
            autorizarProcedimento(execution);
        }
    }
}

// ✅ CORRETO - Um Delegate ou Service method por tarefa
// BPMN: camunda:expression="${tissService.validarGuia(execution)}"
// BPMN: camunda:expression="${tissService.autorizarProcedimento(execution)}"
```

================================================================================
BOUNDARY EVENTS - SEMPRE COM SAÍDA
================================================================================

⚠️ **ERRO CRÍTICO:** Boundary Event sem sequenceFlow é INÚTIL!

**BPMN CORRETO:**
```xml
<!-- Tarefa com Boundary Timer -->
<bpmn:serviceTask id="Task_AguardarResposta"
                  name="Aguardar Resposta"
                  camunda:delegateExpression="${aguardarRespostaDelegate}">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Sucesso</bpmn:outgoing>
</bpmn:serviceTask>

<!-- Boundary Timer - DEVE TER outgoing! -->
<bpmn:boundaryEvent id="Boundary_Timeout30min"
                    name="Timeout 30min"
                    attachedToRef="Task_AguardarResposta"
                    cancelActivity="true">
  <bpmn:outgoing>Flow_Timeout</bpmn:outgoing>  <!-- ⚠️ OBRIGATÓRIO -->
  <bpmn:timerEventDefinition id="Timer_30min">
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT30M</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:boundaryEvent>

<!-- O timeout DEVE ir para algum lugar -->
<bpmn:sequenceFlow id="Flow_Timeout"
                   sourceRef="Boundary_Timeout30min"
                   targetRef="Task_TratarTimeout" />

<bpmn:serviceTask id="Task_TratarTimeout"
                  name="Tratar Timeout"
                  camunda:delegateExpression="${tratarTimeoutDelegate}">
  <bpmn:incoming>Flow_Timeout</bpmn:incoming>
  <bpmn:outgoing>Flow_FimTimeout</bpmn:outgoing>
</bpmn:serviceTask>
```

================================================================================
SUBPROCESSOS - ESCOPO DE VARIÁVEIS
================================================================================

**BPMN:**
```xml
<bpmn:subProcess id="SubProcess_Validacao" name="Validação Completa">
  <bpmn:incoming>Flow_In</bpmn:incoming>
  <bpmn:outgoing>Flow_Out</bpmn:outgoing>

  <bpmn:startEvent id="Start_Sub">
    <bpmn:outgoing>Flow_Sub_1</bpmn:outgoing>
  </bpmn:startEvent>

  <bpmn:serviceTask id="Task_Sub_Validar"
                    name="Validar Dados"
                    camunda:delegateExpression="${validarDadosDelegate}">
    <bpmn:incoming>Flow_Sub_1</bpmn:incoming>
    <bpmn:outgoing>Flow_Sub_2</bpmn:outgoing>
  </bpmn:serviceTask>

  <bpmn:endEvent id="End_Sub">
    <bpmn:incoming>Flow_Sub_2</bpmn:incoming>
  </bpmn:endEvent>

  <bpmn:sequenceFlow id="Flow_Sub_1" sourceRef="Start_Sub" targetRef="Task_Sub_Validar" />
  <bpmn:sequenceFlow id="Flow_Sub_2" sourceRef="Task_Sub_Validar" targetRef="End_Sub" />
</bpmn:subProcess>
```

**Java - Variáveis em Subprocesso:**
```java
@Component("validarDadosDelegate")
public class ValidarDadosDelegate implements JavaDelegate {

    @Override
    public void execute(DelegateExecution execution) {
        // Variáveis do processo pai estão disponíveis
        String cpf = (String) execution.getVariable("cpf_paciente");

        // Variáveis criadas aqui ficam disponíveis no processo pai
        // (a menos que o subprocesso seja de escopo isolado)
        execution.setVariable("validacao_completa", true);

        // Para variável LOCAL (só no subprocesso):
        execution.setVariableLocal("contador_interno", 0);
    }
}
```

================================================================================
EXTERNAL TASK vs JAVA DELEGATE - QUANDO USAR CADA UM
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ JAVA DELEGATE                        │ EXTERNAL TASK (Worker)              │
├──────────────────────────────────────┼─────────────────────────────────────┤
│ ✅ Código Java no mesmo projeto     │ ✅ Código em outra linguagem         │
│ ✅ Precisa de transação do Camunda  │ ✅ Precisa escalar independente      │
│ ✅ Execução rápida (< 30s)          │ ✅ Execução longa (minutos)          │
│ ✅ Acesso direto a beans Spring     │ ✅ Isolamento de falhas              │
│ ✅ Deploy junto com Camunda         │ ✅ Deploy independente               │
│                                      │                                      │
│ ❌ Não escala independente          │ ❌ Latência de polling               │
│ ❌ Falha afeta engine               │ ❌ Mais complexo de configurar       │
└──────────────────────────────────────┴─────────────────────────────────────┘

⚠️ **NUNCA MISTURE:**
```xml
<!-- ❌ ERRADO: External Task com classe Java -->
<bpmn:serviceTask camunda:type="external"
                  camunda:topic="meu-topic"
                  camunda:class="com.empresa.MeuDelegate">  <!-- IGNORADO! -->

<!-- ✅ CORRETO: External Task -->
<bpmn:serviceTask camunda:type="external"
                  camunda:topic="meu-topic">

<!-- ✅ CORRETO: Java Delegate -->
<bpmn:serviceTask camunda:delegateExpression="${meuDelegate}">
```

================================================================================
ESTRUTURA DE PACOTES JAVA
================================================================================

```
src/main/java/com/empresa/
├── delegates/                    # JavaDelegates
│   ├── autorizacao/
│   │   ├── ValidarGuiaDelegate.java
│   │   ├── AutorizarProcedimentoDelegate.java
│   │   └── NotificarBeneficiarioDelegate.java
│   ├── nps/
│   │   ├── EnviarPesquisaNpsDelegate.java
│   │   ├── ProcessarRespostaNpsDelegate.java
│   │   └── AnalisarSentimentoDelegate.java
│   └── reclamacoes/
│       ├── RegistrarReclamacaoDelegate.java
│       ├── AnalisarCausaRaizDelegate.java
│       └── RegistrarResolucaoDelegate.java
├── services/                     # Services reutilizáveis
│   ├── TissService.java
│   ├── NotificacaoService.java
│   └── NpsService.java
├── repositories/                 # Acesso a dados
│   ├── GuiaRepository.java
│   └── ReclamacaoRepository.java
└── config/                       # Configurações
    └── CamundaConfig.java
```

================================================================================
TEMPLATE DE DELEGATE COMPLETO
================================================================================

```java
package com.empresa.delegates.exemplo;

import org.camunda.bpm.engine.delegate.BpmnError;
import org.camunda.bpm.engine.delegate.DelegateExecution;
import org.camunda.bpm.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Delegate: Nome da Tarefa
 * ========================
 *
 * Responsabilidade TÉCNICA (não contém regras de negócio):
 * - [Descrever ação técnica]
 *
 * O BPMN já definiu que esta tarefa deve ser executada.
 * O código NÃO decide caminhos do processo.
 *
 * INPUT (variáveis esperadas):
 * - variavel_1 (String): Descrição
 * - variavel_2 (Integer): Descrição
 *
 * OUTPUT (variáveis criadas):
 * - resultado_1 (Boolean): Descrição
 * - resultado_2 (String): Descrição
 *
 * ERROS (BpmnError):
 * - ERRO_VALIDACAO: Dados de entrada inválidos
 * - ERRO_INTEGRACAO: Falha na integração externa
 */
@Component("exemploDelegate")
public class ExemploDelegate implements JavaDelegate {

    private static final Logger logger = LoggerFactory.getLogger(ExemploDelegate.class);

    // Códigos de erro para Boundary Error Events
    private static final String ERRO_VALIDACAO = "ERRO_VALIDACAO";
    private static final String ERRO_INTEGRACAO = "ERRO_INTEGRACAO";

    @Autowired
    private ExemploService exemploService;

    @Override
    public void execute(DelegateExecution execution) throws Exception {
        String activityId = execution.getCurrentActivityId();
        String processInstanceId = execution.getProcessInstanceId();
        String businessKey = execution.getBusinessKey();

        logger.info("[{}] Iniciando delegate - Process: {}, BusinessKey: {}",
                    activityId, processInstanceId, businessKey);

        try {
            // 1. LER variáveis de entrada
            String variavel1 = getRequiredVariable(execution, "variavel_1", String.class);
            Integer variavel2 = getOptionalVariable(execution, "variavel_2", Integer.class, 0);

            logger.debug("[{}] Variáveis lidas - var1: {}, var2: {}", activityId, variavel1, variavel2);

            // 2. EXECUTAR lógica técnica
            ResultadoDTO resultado = exemploService.executar(variavel1, variavel2);

            // 3. ESCREVER variáveis de saída
            execution.setVariable("resultado_1", resultado.isSucesso());
            execution.setVariable("resultado_2", resultado.getMensagem());
            execution.setVariable("delegate_status", "SUCESSO");

            logger.info("[{}] Delegate concluído com sucesso - Resultado: {}",
                        activityId, resultado.isSucesso());

        } catch (ValidacaoException e) {
            logger.error("[{}] Erro de validação: {}", activityId, e.getMessage());
            execution.setVariable("delegate_status", "ERRO_VALIDACAO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw new BpmnError(ERRO_VALIDACAO, e.getMessage());

        } catch (IntegracaoException e) {
            logger.error("[{}] Erro de integração: {}", activityId, e.getMessage(), e);
            execution.setVariable("delegate_status", "ERRO_INTEGRACAO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw new BpmnError(ERRO_INTEGRACAO, e.getMessage());

        } catch (Exception e) {
            logger.error("[{}] Erro inesperado: {}", activityId, e.getMessage(), e);
            execution.setVariable("delegate_status", "ERRO");
            execution.setVariable("delegate_erro", e.getMessage());
            throw e; // Re-throw para Camunda marcar como incident
        }
    }

    /**
     * Obtém variável obrigatória do processo.
     * @throws IllegalArgumentException se variável não existir ou for nula
     */
    @SuppressWarnings("unchecked")
    private <T> T getRequiredVariable(DelegateExecution execution, String name, Class<T> type) {
        Object value = execution.getVariable(name);
        if (value == null) {
            throw new IllegalArgumentException("Variável obrigatória não encontrada: " + name);
        }
        return (T) value;
    }

    /**
     * Obtém variável opcional do processo com valor default.
     */
    @SuppressWarnings("unchecked")
    private <T> T getOptionalVariable(DelegateExecution execution, String name, Class<T> type, T defaultValue) {
        Object value = execution.getVariable(name);
        return value != null ? (T) value : defaultValue;
    }
}
```

================================================================================
CHECKLIST DE VALIDAÇÃO BPMN + DELEGATES
================================================================================

Para cada Service Task no BPMN, verifique:

**Configuração:**
- [ ] Tipo de invocação correto (class, delegateExpression, expression, external)
- [ ] Nome do bean corresponde ao @Component
- [ ] Pacote Java está correto e compila

**Boundary Events:**
- [ ] Todos os Boundary Events têm sequenceFlow de saída
- [ ] Timer Events usam formato correto (PT30M, PT1H, etc)
- [ ] Error Events referenciam códigos de erro do Delegate

**Variáveis:**
- [ ] Delegate documenta variáveis de INPUT
- [ ] Delegate documenta variáveis de OUTPUT
- [ ] Variáveis obrigatórias são validadas
- [ ] Gateway conditions usam variáveis que existem

**Fluxo:**
- [ ] Todos os sequenceFlow conectam elementos existentes
- [ ] Gateways têm todas as saídas com condições
- [ ] End Events são alcançáveis

================================================================================
ERROS COMUNS E SOLUÇÕES
================================================================================

| Erro | Causa | Solução |
|------|-------|---------|
| `Unknown property used in expression: ${bean}` | Bean não registrado | Adicionar @Component("bean") |
| `Cannot resolve identifier 'execution'` | Usando expression sem passar execution | Usar `${service.metodo(execution)}` |
| `No matching constructor found` | Delegate sem construtor default | Remover @Autowired do construtor |
| `Incident: job failed` | Exceção não tratada | Adicionar try-catch e BpmnError |
| Timer não dispara | Boundary sem sequenceFlow | Adicionar outgoing flow |
| Variável nula | Processo anterior não criou | Validar variável no Delegate |

================================================================================
```

---

## Referências Rápidas

### Configuração BPMN por Tipo

| Tipo | Atributo BPMN | Exemplo |
|------|---------------|---------|
| Classe direta | `camunda:class` | `camunda:class="com.empresa.MeuDelegate"` |
| Spring Bean | `camunda:delegateExpression` | `camunda:delegateExpression="${meuDelegate}"` |
| Método específico | `camunda:expression` | `camunda:expression="${service.metodo(execution)}"` |
| Worker externo | `camunda:type` + `camunda:topic` | `camunda:type="external" camunda:topic="meu-topic"` |

### Formato de Timers

| Duração | Formato ISO 8601 |
|---------|------------------|
| 30 minutos | `PT30M` |
| 1 hora | `PT1H` |
| 1 dia | `P1D` |
| 2 horas e 30 min | `PT2H30M` |

### Códigos de Erro BPMN

```java
// No Delegate
throw new BpmnError("ERRO_VALIDACAO", "Mensagem");

// No BPMN - Boundary Error Event
<bpmn:boundaryEvent attachedToRef="Task_ID">
  <bpmn:errorEventDefinition errorRef="Error_ERRO_VALIDACAO" />
</bpmn:boundaryEvent>

<bpmn:error id="Error_ERRO_VALIDACAO" name="Erro Validação" errorCode="ERRO_VALIDACAO" />
```

---

## Versionamento

| Versão | Data | Alterações |
|--------|------|------------|
| 1.0 | 2024-12 | Versão inicial |
