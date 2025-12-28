"""
OpenTelemetry setup for traces, metrics, and logs exported to Datadog.
"""
import os
from typing import Dict, Optional, Union

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_observability() -> None:
    """Configure OpenTelemetry with OTLP exporter for Datadog."""
    
    # Parse OTLP headers
    otlp_headers_str = os.getenv('OTEL_EXPORTER_OTLP_HEADERS', '')
    otlp_headers = {}
    if otlp_headers_str:
        for header in otlp_headers_str.split(','):
            if '=' in header:
                key, value = header.split('=', 1)
                otlp_headers[key.strip()] = value.strip()
    
    # Get OTLP endpoint (defaults to Datadog)
    otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'https://api.datadoghq.com')
    service_name = os.getenv('OTEL_SERVICE_NAME', 'llm-ops-watchtower')
    
    # Create resource with service information
    resource = Resource.create({
        'service.name': service_name,
        'service.version': '1.0.0',
        'deployment.environment': os.getenv('DEPLOYMENT_ENVIRONMENT', 'production'),
    })
    
    # Setup tracing
    trace_provider = TracerProvider(resource=resource)
    
    # Configure OTLP trace exporter
    trace_endpoint = f"{otlp_endpoint}/api/v2/traces"
    trace_exporter = OTLPSpanExporter(
        endpoint=trace_endpoint,
        headers=otlp_headers,
    )
    
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    
    # Setup metrics
    metrics_endpoint = f"{otlp_endpoint}/api/v2/metrics"
    metric_exporter = OTLPMetricExporter(
        endpoint=metrics_endpoint,
        headers=otlp_headers,
    )
    
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=10000,  # Export every 10 seconds
    )
    
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)
    
    # Get meters and tracers
    meter = metrics.get_meter(__name__)
    tracer = trace.get_tracer(__name__)
    
    return meter, tracer


def create_metrics(meter: metrics.Meter) -> Dict[str, Union[metrics.Counter, metrics.Histogram]]:
    """Create and return common metrics."""
    return {
        'request_count': meter.create_counter(
            name='llm.requests.total',
            description='Total number of LLM requests',
            unit='1',
        ),
        'request_latency': meter.create_histogram(
            name='llm.request.latency',
            description='Request latency in milliseconds',
            unit='ms',
        ),
        'llm_latency': meter.create_histogram(
            name='llm.generate.latency',
            description='LLM generation latency in milliseconds',
            unit='ms',
        ),
        'tokens_in': meter.create_counter(
            name='llm.tokens.input',
            description='Total input tokens',
            unit='1',
        ),
        'tokens_out': meter.create_counter(
            name='llm.tokens.output',
            description='Total output tokens',
            unit='1',
        ),
        'failures': meter.create_counter(
            name='llm.failures.total',
            description='Total number of LLM failures',
            unit='1',
        ),
        'prompt_injection_count': meter.create_counter(
            name='llm.security.prompt_injection',
            description='Number of prompt injection attempts detected',
            unit='1',
        ),
        'pii_leak_count': meter.create_counter(
            name='llm.security.pii_detected',
            description='Number of PII detections',
            unit='1',
        ),
    }


def get_tracer() -> trace.Tracer:
    """Get the OpenTelemetry tracer."""
    return trace.get_tracer(__name__)


def get_meter() -> metrics.Meter:
    """Get the OpenTelemetry meter."""
    return metrics.get_meter(__name__)

