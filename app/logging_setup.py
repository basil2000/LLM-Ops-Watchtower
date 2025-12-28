"""
JSON structured logging setup with trace correlation.
"""
import json
import logging
import os
from typing import Any, Dict

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes trace correlation."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add trace_id from OpenTelemetry context if available
        try:
            from opentelemetry import trace
            
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                trace_id = format(span.get_span_context().trace_id, '032x')
                log_record['trace_id'] = trace_id
                log_record['span_id'] = format(span.get_span_context().span_id, '016x')
        except Exception:
            # If OpenTelemetry is not available or trace context is missing, skip
            pass
        
        # Ensure timestamp is in ISO format
        if 'timestamp' not in log_record:
            log_record['timestamp'] = self.formatTime(record, self.datefmt)


def setup_logging() -> None:
    """Configure JSON structured logging."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

