# LLM Ops Watchtower - System Design Documentation

## Table of Contents

1. [High-Level Design (HLD)](#high-level-design-hld)
   - [System Architecture](#system-architecture)
   - [Component Overview](#component-overview)
   - [Data Flow](#data-flow)
   - [Technology Stack](#technology-stack)

2. [Low-Level Design (LLD)](#low-level-design-lld)
   - [FastAPI Application](#fastapi-application)
   - [LLM Integration](#llm-integration)
   - [Security Module](#security-module)
   - [Observability Module](#observability-module)
   - [Logging System](#logging-system)

---

## High-Level Design (HLD)

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Web Browser (static/index.html)                         │  │
│  │  - Single Page Application                               │  │
│  │  - RESTful API Client                                    │  │
│  │  - Session Management                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/HTTPS
                              │ JSON Request/Response
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (app/main.py)                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │   Routes     │  │  Middleware  │  │  Lifecycle   │  │  │
│  │  │  - GET /     │  │  - OpenTel   │  │  Management  │  │  │
│  │  │  - POST /chat│  │  - CORS      │  │  - Startup   │  │  │
│  │  │  - GET /health│  │  - Auth     │  │  - Shutdown  │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Security    │    │   LLM        │    │ Observability│
│  Module      │    │  Integration │    │   Module     │
│              │    │              │    │              │
│  - Injection │    │  - Gemini    │    │  - Traces    │
│    Detection │    │    Client    │    │  - Metrics   │
│  - PII       │    │  - Token     │    │  - Export    │
│    Detection │    │    Tracking  │    │              │
└──────────────┘    └──────┬───────┘    └──────┬───────┘
                           │                    │
                           │                    │
                           ▼                    ▼
              ┌────────────────────────┐  ┌──────────────┐
              │  Google Vertex AI      │  │   Datadog    │
              │  - Gemini API          │  │   Platform   │
              │  - Token Usage         │  │              │
              │  - Response Generation │  │  - APM       │
              └────────────────────────┘  │  - Metrics   │
                                          │  - Logs      │
                                          │  - Monitors  │
                                          └──────────────┘
```

### Component Overview

#### 1. Frontend Layer (static/index.html)
- **Purpose**: Single-page web interface for user interaction
- **Technology**: Vanilla JavaScript, HTML5, CSS3
- **Responsibilities**:
  - Render chat interface
  - Handle user input
  - Send HTTP requests to backend
  - Display responses and errors
  - Manage session state

#### 2. Application Layer (app/main.py)
- **Purpose**: RESTful API server and request orchestration
- **Technology**: FastAPI, Python 3.11+
- **Responsibilities**:
  - Route HTTP requests
  - Coordinate security, LLM, and observability modules
  - Manage application lifecycle
  - Error handling and response formatting
  - Static file serving

#### 3. Security Module (app/security.py)
- **Purpose**: Input validation and threat detection
- **Responsibilities**:
  - Pattern-based prompt injection detection
  - PII (Personally Identifiable Information) detection
  - Prompt hashing for logging
  - Security event flagging

#### 4. LLM Integration Module (app/llm.py)
- **Purpose**: Interface with Google Vertex AI Gemini
- **Responsibilities**:
  - Initialize Vertex AI client
  - Generate LLM responses
  - Extract token usage metadata
  - Handle API errors and retries

#### 5. Observability Module (app/observability.py)
- **Purpose**: Distributed tracing and metrics collection
- **Technology**: OpenTelemetry SDK
- **Responsibilities**:
  - Create and manage spans
  - Export traces to Datadog via OTLP
  - Create and record metrics
  - Configure resource attributes

#### 6. Logging System (app/logging_setup.py)
- **Purpose**: Structured logging with trace correlation
- **Technology**: Python logging, python-json-logger
- **Responsibilities**:
  - JSON-formatted log output
  - Trace ID injection into logs
  - Log level configuration
  - Third-party log noise reduction

### Data Flow

#### Request Flow

```
1. User Input → Frontend
   ↓
2. HTTP POST /chat → FastAPI Router
   ↓
3. Request ID Generation (UUID4)
   ↓
4. Root Span Creation (OpenTelemetry)
   ↓
5. Security Analysis Span
   ├── Prompt Injection Check
   ├── PII Detection
   ├── Prompt Hashing
   └── Metrics Update (if threats detected)
   ↓
6. LLM Request Span
   ├── Vertex AI Client Call
   ├── Token Usage Extraction
   ├── Response Generation
   └── Latency Measurement
   ↓
7. Span Attributes & Metrics Recording
   ↓
8. Structured Logging
   ↓
9. JSON Response → Frontend
   ↓
10. Span Export to Datadog (async)
```

#### Observability Data Flow

```
Application Code
    ↓
OpenTelemetry SDK
    ├──→ Traces (via OTLP HTTP) → Datadog APM
    ├──→ Metrics (via OTLP HTTP) → Datadog Metrics
    └──→ Logs (via stdout) → Datadog Logs (via collector)
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Web Framework | FastAPI | 0.109.0 | REST API server |
| ASGI Server | Uvicorn | 0.27.0 | Production server |
| LLM Provider | Google Vertex AI | 1.71.1 | Gemini model access |
| Observability | OpenTelemetry | 1.22.0 | Traces and metrics |
| Logging | python-json-logger | 2.0.7 | Structured logging |
| Configuration | python-dotenv | 1.0.0 | Environment management |
| Containerization | Docker | Latest | Deployment packaging |
| Cloud Platform | Google Cloud Run | - | Serverless hosting |
| Monitoring | Datadog | - | APM, metrics, logs |

---

## Low-Level Design (LLD)

### FastAPI Application

#### Module: app/main.py

**Class Structure**: No classes, functional approach with global state

**Global Variables**:
```python
gemini_client: Optional[GeminiClient]  # LLM client instance
app_metrics: Dict[str, Union[Counter, Histogram]]  # OpenTelemetry metrics
tracer: Tracer  # OpenTelemetry tracer instance
logger: Logger  # Application logger
```

**Functions**:

1. **lifespan(app: FastAPI) → AsyncContextManager**
   - **Purpose**: Application lifecycle management
   - **Responsibilities**:
     - Initialize Gemini client on startup
     - Handle graceful shutdown
   - **Error Handling**: Allows app to start even if Gemini client fails

2. **root() → HTMLResponse**
   - **Purpose**: Serve static HTML chat interface
   - **Route**: GET /
   - **Returns**: HTML content from static/index.html

3. **chat(request: ChatRequest, ...) → ChatResponse**
   - **Purpose**: Main chat endpoint
   - **Route**: POST /chat
   - **Parameters**:
     - `request: ChatRequest` - Message and session ID
     - `slow_mode: Optional[bool]` - Testing parameter
     - `simulate_failure: Optional[bool]` - Testing parameter
   - **Flow**:
     1. Generate request_id (UUID4)
     2. Create root span
     3. Security analysis (child span)
     4. LLM generation (child span)
     5. Record metrics
     6. Log structured data
     7. Return response
   - **Error Handling**: Catches exceptions, records on span, returns HTTP 500

4. **health() → Dict**
   - **Purpose**: Health check endpoint
   - **Route**: GET /health
   - **Returns**: Service status and Gemini availability

**Data Models**:

```python
class ChatRequest(BaseModel):
    session_id: str  # User session identifier
    message: str     # User input message

class ChatResponse(BaseModel):
    response: str    # LLM generated response
    request_id: str  # Unique request identifier
```

### LLM Integration

#### Module: app/llm.py

**Class: GeminiClient**

**Attributes**:
- `model_name: str` - Gemini model identifier
- `project_id: str` - Google Cloud project ID
- `location: str` - Vertex AI region

**Methods**:

1. **__init__(self)**
   - **Purpose**: Initialize Vertex AI client
   - **Configuration**: Reads from environment variables
   - **Raises**: ValueError if GOOGLE_CLOUD_PROJECT not set
   - **Side Effects**: Calls `vertexai.init()`

2. **generate(self, prompt: str, request_id: str) → Tuple[str, Dict[str, int], float]**
   - **Purpose**: Generate LLM response
   - **Parameters**:
     - `prompt: str` - Input text
     - `request_id: str` - Request identifier for logging
   - **Returns**:
     - `response_text: str` - Generated text
     - `token_counts: Dict[str, int]` - {"tokens_in": int, "tokens_out": int}
     - `latency_ms: float` - Generation time in milliseconds
   - **Error Handling**: Logs exceptions, re-raises for caller handling
   - **Token Extraction**: Attempts multiple attribute paths for compatibility

**Token Usage Extraction Logic**:
```python
if hasattr(response, 'usage_metadata'):
    usage = response.usage_metadata
    # Try prompt_token_count / candidates_token_count
    # Fallback to prompt_token_counts / candidates_token_counts (lists)
    # Fallback to total_token_count estimation
```

### Security Module

#### Module: app/security.py

**Constants**:

```python
PROMPT_INJECTION_PATTERNS: List[str]
# Regex patterns for common injection attempts:
# - "ignore previous instructions"
# - "act as", "pretend to be"
# - System token markers
# - Secret extraction attempts

PII_PATTERNS: Dict[str, str]
# Regex patterns for PII detection:
# - email: RFC 5322 compliant pattern
# - ssn: XXX-XX-XXXX format
# - credit_card: 16-digit patterns
# - phone: US phone number formats
# - ip_address: IPv4 addresses
```

**Functions**:

1. **hash_prompt(prompt: str) → str**
   - **Purpose**: Generate SHA256 hash for logging
   - **Input**: Raw prompt string
   - **Output**: 64-character hex string

2. **redact_preview(prompt: str, max_length: int = 50) → str**
   - **Purpose**: Create safe preview for logs
   - **Logic**: Shows first 20 + "..." + last 20 chars if length exceeds max_length

3. **check_prompt_injection(prompt: str) → bool**
   - **Purpose**: Detect injection attempts
   - **Algorithm**: Regex pattern matching against PROMPT_INJECTION_PATTERNS
   - **Returns**: True if any pattern matches

4. **detect_pii(prompt: str) → Dict[str, int]**
   - **Purpose**: Identify PII types and counts
   - **Returns**: Dictionary mapping PII type to detection count
   - **Example**: {"email": 2, "phone": 1}

5. **analyze_security(prompt: str) → Dict[str, Any]**
   - **Purpose**: Comprehensive security analysis
   - **Returns**:
     ```python
     {
         "prompt_injection": bool,
         "pii_detected": bool,
         "pii_types": Dict[str, int],
         "prompt_hash": str,
         "prompt_preview": str
     }
     ```

### Observability Module

#### Module: app/observability.py

**Functions**:

1. **setup_observability() → Tuple[Meter, Tracer]**
   - **Purpose**: Configure OpenTelemetry SDK
   - **Configuration Sources**: Environment variables
   - **Setup Steps**:
     1. Parse OTLP headers (for Datadog API key)
     2. Create Resource with service metadata
     3. Configure TracerProvider with OTLP exporter
     4. Configure MeterProvider with OTLP exporter
     5. Return meter and tracer instances
   - **Endpoints**: 
     - Traces: `{endpoint}/api/v2/traces`
     - Metrics: `{endpoint}/api/v2/metrics`

2. **create_metrics(meter: Meter) → Dict[str, Union[Counter, Histogram]]**
   - **Purpose**: Define application metrics
   - **Returns**: Dictionary of metric instruments
   - **Metrics Defined**:
     ```python
     {
         "request_count": Counter,        # llm.requests.total
         "request_latency": Histogram,    # llm.request.latency (ms)
         "llm_latency": Histogram,        # llm.generate.latency (ms)
         "tokens_in": Counter,            # llm.tokens.input
         "tokens_out": Counter,           # llm.tokens.output
         "failures": Counter,             # llm.failures.total
         "prompt_injection_count": Counter,  # llm.security.prompt_injection
         "pii_leak_count": Counter       # llm.security.pii_detected
     }
     ```

**Span Structure**:

```
chat.request (root span)
├── Attributes:
│   ├── http.method: POST
│   ├── http.route: /chat
│   ├── session_id: string
│   ├── request_id: UUID
│   ├── llm.model: string
│   ├── request.latency_ms: float
│   ├── security.prompt_injection: bool
│   ├── security.pii_detected: bool
│   ├── security.prompt_hash: string
│   ├── llm.tokens_in: int
│   └── llm.tokens_out: int
│
├── security.check (child span)
│   ├── Attributes:
│   │   ├── security.prompt_injection: bool
│   │   ├── security.pii_detected: bool
│   │   ├── security.prompt_hash: string
│   │   └── security.pii_types: string
│
└── llm.request (child span)
    ├── Attributes:
    │   ├── llm.model: string
    │   ├── llm.tokens_in: int
    │   ├── llm.tokens_out: int
    │   └── llm.latency_ms: float
    └── Events: Exception records (if errors)
```

### Logging System

#### Module: app/logging_setup.py

**Class: CustomJsonFormatter**

**Inheritance**: `jsonlogger.JsonFormatter`

**Methods**:

1. **add_fields(log_record, record, message_dict) → None**
   - **Purpose**: Inject trace context into log records
   - **Logic**:
     1. Call parent formatter
     2. Extract trace_id and span_id from OpenTelemetry context
     3. Add to log_record if available
     4. Ensure ISO timestamp format

**Functions**:

1. **setup_logging() → None**
   - **Purpose**: Configure application-wide logging
   - **Configuration**:
     - Log level from LOG_LEVEL env var (default: INFO)
     - JSON formatter to stdout
     - Reduced verbosity for third-party libraries

**Log Record Structure**:

```json
{
    "timestamp": "ISO-8601 datetime",
    "level": "INFO|WARNING|ERROR",
    "name": "module.name",
    "message": "Log message",
    "trace_id": "32-character hex (optional)",
    "span_id": "16-character hex (optional)",
    "request_id": "UUID (from extra dict)",
    "session_id": "string (from extra dict)",
    "model": "string (from extra dict)",
    "latency_ms": "float (from extra dict)",
    ...additional fields from extra dict...
}
```

---

## Component Interactions

### Request Processing Sequence

1. **Client sends POST /chat**
   - FastAPI receives request
   - OpenTelemetry middleware creates HTTP span

2. **Route Handler Execution**
   - `chat()` function called
   - Request ID generated
   - Root span created explicitly

3. **Security Analysis**
   - `analyze_security()` called
   - Regex patterns matched
   - Metrics updated if threats found
   - Results attached to span

4. **LLM Generation**
   - `GeminiClient.generate()` called
   - Vertex AI API request
   - Token usage extracted
   - Response returned

5. **Observability Recording**
   - Span attributes set
   - Metrics recorded
   - Structured log written

6. **Response Return**
   - JSON response formatted
   - Span context manager exits (auto-export)
   - Client receives response

### Error Handling Flow

```
Exception Occurs
    ↓
Caught in try/except
    ↓
Record exception on span (root_span.record_exception())
    ↓
Set span status to ERROR
    ↓
Increment failure metric
    ↓
Log error with trace_id
    ↓
Return HTTP 500 with error detail
    ↓
Span exported with error context
```

### Metrics Recording

```python
# Counter example
app_metrics['request_count'].add(1, {})

# Histogram example
app_metrics['request_latency'].record(1250.5, {})

# Counter with attributes
app_metrics['pii_leak_count'].add(1, {'pii_type': 'email'})
```

Metrics are exported asynchronously every 10 seconds to Datadog via OTLP HTTP.

---

## Data Structures

### Request Flow State

```python
{
    "request_id": "uuid4 string",
    "session_id": "user-provided string",
    "start_time": "float (timestamp)",
    "security_result": {
        "prompt_injection": bool,
        "pii_detected": bool,
        "pii_types": Dict[str, int],
        "prompt_hash": str,
        "prompt_preview": str
    },
    "llm_result": {
        "response_text": str,
        "token_counts": {"tokens_in": int, "tokens_out": int},
        "latency_ms": float
    },
    "total_latency_ms": float
}
```

### Span Context Propagation

OpenTelemetry automatically propagates trace context via:
- W3C Trace Context headers
- In-process context variables
- Async context managers

This ensures all spans in a request share the same trace_id.

---

## Configuration Management

### Environment Variables

| Variable | Module | Usage |
|----------|--------|-------|
| GOOGLE_CLOUD_PROJECT | llm.py | Vertex AI initialization |
| VERTEX_LOCATION | llm.py | Vertex AI region |
| GEMINI_MODEL | llm.py | Model selection |
| OTEL_EXPORTER_OTLP_ENDPOINT | observability.py | Datadog endpoint |
| OTEL_EXPORTER_OTLP_HEADERS | observability.py | API key authentication |
| OTEL_SERVICE_NAME | observability.py | Service identification |
| LOG_LEVEL | logging_setup.py | Logging verbosity |

### Configuration Loading Order

1. `.env` file (via python-dotenv)
2. System environment variables
3. Default values (hardcoded)

---

## Deployment Architecture

### Container Structure

```
Docker Container
├── Base: python:3.11-slim
├── Working Directory: /app
├── User: appuser (non-root)
├── Exposed Port: 8080
├── Health Check: GET /health
└── Command: uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Cloud Run Configuration

- **Platform**: Managed
- **Memory**: 2Gi
- **CPU**: 2 vCPU
- **Timeout**: 300 seconds
- **Min Instances**: 0 (scale to zero)
- **Max Instances**: 10
- **Concurrency**: Default (80)

---

## Performance Considerations

### Latency Optimization

1. **Async Operations**: FastAPI async endpoints
2. **Span Batching**: OpenTelemetry batches span exports
3. **Metric Batching**: 10-second export interval
4. **Log Buffering**: Python logging buffers to stdout

### Scalability

1. **Stateless Design**: No server-side session storage
2. **Horizontal Scaling**: Cloud Run auto-scales instances
3. **Connection Pooling**: Vertex AI client manages connections
4. **Resource Limits**: Container memory/CPU constraints

### Observability Overhead

- **Tracing**: ~1-5ms per span creation
- **Metrics**: Negligible (in-memory aggregation)
- **Logging**: ~0.1ms per log entry
- **OTLP Export**: Async, non-blocking

---

## Security Considerations

### Input Validation

- Regex-based pattern matching (heuristic, not exhaustive)
- No actual blocking of requests (monitoring only)
- Prompt hashing prevents sensitive data in logs

### Data Privacy

- PII detection logged but not redacted from LLM input
- Prompt previews truncated in logs
- Full prompts never logged (hash only)

### Authentication

- Currently: None (public endpoint)
- Production: Add API key or OAuth middleware
- Cloud Run: Can use IAM-based authentication

---

## Extension Points

### Adding New Metrics

1. Define metric in `observability.create_metrics()`
2. Record metric in application code
3. Add to Datadog dashboard configuration

### Adding Security Rules

1. Add pattern to `PROMPT_INJECTION_PATTERNS` or `PII_PATTERNS`
2. Update `analyze_security()` if needed
3. Create corresponding Datadog monitor

### Adding New Endpoints

1. Define route in `app/main.py`
2. Create request/response models
3. Add observability spans as needed
4. Update health check if required

