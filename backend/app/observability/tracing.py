import logging
from contextlib import contextmanager
from typing import Any, Optional

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)

_tracer = None


def setup_tracing(app: FastAPI):
    global _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": "ai-agent-platform",
            "service.version": "1.0.0",
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer("ai-agent-platform")

        FastAPIInstrumentor.instrument_app(app)

        logger.info("OpenTelemetry tracing initialized (endpoint=%s)", settings.OTLP_ENDPOINT)
    except ImportError:
        logger.warning("OpenTelemetry packages not installed — tracing disabled")
    except Exception as exc:
        logger.warning("Failed to initialize OpenTelemetry tracing: %s", exc)


def get_tracer():
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer("ai-agent-platform")
        except ImportError:
            return None
    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
):
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        yield span


def trace_workflow_execution(workflow_id: str, execution_id: str):
    return trace_span(
        "workflow.execute",
        attributes={"workflow.id": workflow_id, "execution.id": execution_id},
    )


def trace_agent_invocation(agent_id: str, agent_name: str, node_id: str = ""):
    return trace_span(
        "agent.invoke",
        attributes={"agent.id": agent_id, "agent.name": agent_name, "node.id": node_id},
    )


def trace_llm_call(model: str, agent_id: str = ""):
    return trace_span(
        "llm.call",
        attributes={"llm.model": model, "agent.id": agent_id},
    )


def trace_tool_execution(tool_name: str, agent_id: str = ""):
    return trace_span(
        "tool.execute",
        attributes={"tool.name": tool_name, "agent.id": agent_id},
    )


def trace_checkpoint_operation(operation: str, thread_id: str = ""):
    return trace_span(
        f"checkpoint.{operation}",
        attributes={"checkpoint.operation": operation, "thread.id": thread_id},
    )
