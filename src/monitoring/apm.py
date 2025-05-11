from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.playwright import PlaywrightInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class APMManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tracer = None
        self._setup_tracing()

    def _setup_tracing(self):
        """Configure OpenTelemetry tracing."""
        try:
            # Configure resource attributes
            resource = Resource.create({
                "service.name": "price-monitor",
                "service.version": "1.0.0",
                "deployment.environment": self.config.get("environment", "production")
            })

            # Create tracer provider
            provider = TracerProvider(resource=resource)
            
            # Configure OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.get("otlp_endpoint", "localhost:4317"),
                insecure=True
            )
            
            # Add span processor
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            
            # Set global tracer provider
            trace.set_tracer_provider(provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Instrument libraries
            PlaywrightInstrumentor().instrument()
            AsyncioInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            
            logger.info("APM tracing configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup APM tracing: {e}")
            raise

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> trace.Span:
        """Start a new span with the given name and attributes."""
        if not self.tracer:
            raise RuntimeError("APM tracing not initialized")
            
        return self.tracer.start_span(name, attributes=attributes)

    def record_metric(self, name: str, value: float, attributes: Optional[Dict[str, Any]] = None):
        """Record a metric with the given name, value and attributes."""
        if not self.tracer:
            raise RuntimeError("APM tracing not initialized")
            
        with self.tracer.start_as_current_span(f"metric.{name}") as span:
            span.set_attribute("metric.value", value)
            if attributes:
                for key, val in attributes.items():
                    span.set_attribute(f"metric.{key}", val)

    def record_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Record an error with context."""
        if not self.tracer:
            raise RuntimeError("APM tracing not initialized")
            
        with self.tracer.start_as_current_span("error") as span:
            span.set_attribute("error.type", type(error).__name__)
            span.set_attribute("error.message", str(error))
            if context:
                for key, val in context.items():
                    span.set_attribute(f"error.context.{key}", val)
            span.set_status(trace.Status(trace.StatusCode.ERROR))

    def cleanup(self):
        """Cleanup APM resources."""
        try:
            # Shutdown tracer provider
            trace.get_tracer_provider().shutdown()
            logger.info("APM tracing cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up APM tracing: {e}") 