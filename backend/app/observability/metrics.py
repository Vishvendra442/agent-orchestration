from prometheus_client import Counter, Histogram, Gauge

agent_invocations_total = Counter(
    "agent_invocations_total",
    "Total number of agent invocations",
    ["agent_id", "agent_name", "status"],
)

agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds",
    "Duration of individual agent node executions",
    ["agent_id"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)

workflow_executions_total = Counter(
    "workflow_executions_total",
    "Total workflow executions",
    ["workflow_id", "status"],
)

workflow_execution_duration_seconds = Histogram(
    "workflow_execution_duration_seconds",
    "Duration of full workflow executions",
    ["workflow_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["agent_id", "token_type"],
)

llm_cost_dollars_total = Counter(
    "llm_cost_dollars_total",
    "Total estimated LLM cost in dollars",
    ["agent_id", "model"],
)

inter_agent_messages_total = Counter(
    "inter_agent_messages_total",
    "Total inter-agent messages sent",
    ["from_agent", "to_agent"],
)

telegram_messages_total = Counter(
    "telegram_messages_total",
    "Total Telegram messages",
    ["direction"],
)

active_workflow_runs = Gauge(
    "active_workflow_runs",
    "Number of currently running workflows",
)

checkpoint_operations_total = Counter(
    "checkpoint_operations_total",
    "Total checkpoint operations",
    ["operation"],
)


def record_agent_invocation(agent_id: str, agent_name: str, status: str, duration_s: float):
    agent_invocations_total.labels(agent_id=agent_id, agent_name=agent_name, status=status).inc()
    agent_execution_duration_seconds.labels(agent_id=agent_id).observe(duration_s)


def record_workflow_execution(workflow_id: str, status: str, duration_s: float):
    workflow_executions_total.labels(workflow_id=workflow_id, status=status).inc()
    workflow_execution_duration_seconds.labels(workflow_id=workflow_id).observe(duration_s)


def record_llm_usage(agent_id: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
    llm_tokens_total.labels(agent_id=agent_id, token_type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(agent_id=agent_id, token_type="completion").inc(completion_tokens)
    llm_cost_dollars_total.labels(agent_id=agent_id, model=model).inc(cost)


def record_telegram_message(direction: str):
    telegram_messages_total.labels(direction=direction).inc()


def record_checkpoint_operation(operation: str):
    checkpoint_operations_total.labels(operation=operation).inc()
