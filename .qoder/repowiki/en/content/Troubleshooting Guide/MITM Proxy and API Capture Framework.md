# MITM Proxy and API Capture Framework

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [MITM_PROXY.md](file://MITM_PROXY.md)
- [MITM_SETUP.md](file://MITM_SETUP.md)
- [capture_api.py](file://capture_api.py)
- [start-mitm-capture.sh](file://start-mitm-capture.sh)
- [core-hub-mitm.sh](file://core-hub-mitm.sh)
- [gluesync_cli.py](file://gluesync_cli.py)
- [gluesync_cli_v2.py](file://gluesync_cli_v2.py)
- [requirements.txt](file://requirements.txt)
- [config.json](file://config.json)
- [docker-compose.yml](file://docker-compose.yml)
- [Makefile](file://Makefile)
- [Dockerfile](file://Dockerfile)
- [Dockerfile.dev](file://Dockerfile.dev)
- [scripts/tcp-proxy.py](file://scripts/tcp-proxy.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [MITM Proxy Components](#mitm-proxy-components)
4. [API Capture Framework](#api-capture-framework)
5. [CLI Integration](#cli-integration)
6. [Containerization Strategy](#containerization-strategy)
7. [Deployment Configuration](#deployment-configuration)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Best Practices](#best-practices)
11. [Conclusion](#conclusion)

## Introduction

The MITM Proxy and API Capture Framework is a comprehensive toolset designed for GlueSync API discovery, reverse engineering, and automation development. This framework enables developers to capture, analyze, and document API interactions between the GlueSync Web UI and Core Hub services, facilitating the creation of automated CLI tools and integration scripts.

The framework consists of three primary components: a Man-in-the-Middle (MITM) proxy for traffic interception, a sophisticated API capture system with structured logging, and a robust CLI interface for programmatic API interaction. Together, these components provide a complete solution for API reverse engineering and automation development.

## System Architecture

The framework operates on a dual-port architecture principle, separating normal operations from capture mode to maintain optimal performance while enabling comprehensive API analysis.

```mermaid
graph TB
subgraph "Client Layer"
UI[Web Browser/UI]
CLI[CLI Tools]
end
subgraph "Traffic Splitting"
P1716[Port 1716<br/>MITM Capture Mode]
P1717[Port 1717<br/>Direct Operation Mode]
P8080[Traefik HTTP<br/>Port 8080]
P8443[Traefik HTTPS<br/>Port 8443]
end
subgraph "Proxy Layer"
MITM[MITM Proxy<br/>Reverse Proxy]
CAP[API Capture<br/>Addon Script]
end
subgraph "Core Hub"
CH[Core Hub API<br/>Port 1717]
SERVICES[GlueSync Services]
end
subgraph "Storage Layer"
LOGS[Captured API Logs<br/>JSON Files]
CONFIG[Configuration Files]
end
UI --> P1716
UI --> P1717
CLI --> P1717
P1716 --> MITM
MITM --> CAP
MITM --> CH
CAP --> LOGS
CH --> SERVICES
P8080 --> CH
P8443 --> CH
```

**Diagram sources**
- [MITM_PROXY.md:37-60](file://MITM_PROXY.md#L37-L60)
- [README.md:41-91](file://README.md#L41-L91)

The architecture implements strict port separation to prevent conflicts between normal operations and capture activities. Port 1716 operates in capture mode with full traffic logging, while port 1717 maintains direct operation mode for optimal performance during regular use.

## MITM Proxy Components

### Core Proxy Infrastructure

The MITM proxy infrastructure consists of several interconnected components working together to provide comprehensive API capture capabilities.

```mermaid
classDiagram
class APICapture {
+logs : List[Dict]
+LOG_FILE : str
+__init__()
+request(flow : HTTPFlow) None
+response(flow : HTTPFlow) None
+load_existing_logs() List[Dict]
+save_logs(logs : List[Dict]) None
}
class StartMitmCapture {
+check_core_hub_running() bool
+check_port_availability(port : int) bool
+clear_previous_capture() None
+start_mitmdump() None
}
class CoreHubMitm {
+cleanup_containers() None
+start_backend_core_hub() None
+start_mitmdump_reverse_proxy() None
}
class MitmProxy {
+mode : str
+listen_port : int
+ssl_insecure : bool
+block_global : bool
+addon_script : str
+forward_target : str
}
APICapture --> MitmProxy : "integrates with"
StartMitmCapture --> MitmProxy : "configures"
CoreHubMitm --> MitmProxy : "deploys"
MitmProxy --> APICapture : "uses addon"
```

**Diagram sources**
- [capture_api.py:30-89](file://capture_api.py#L30-L89)
- [start-mitm-capture.sh:1-51](file://start-mitm-capture.sh#L1-L51)
- [core-hub-mitm.sh:1-49](file://core-hub-mitm.sh#L1-L49)

### Traffic Interception Mechanism

The traffic interception mechanism operates through a sophisticated filtering system that captures only relevant API calls while excluding static assets and unnecessary traffic.

```mermaid
sequenceDiagram
participant Client as "Client Browser"
participant MITM as "MITM Proxy"
participant Filter as "API Filter"
participant CoreHub as "Core Hub"
participant Logger as "Capture Logger"
Client->>MITM : HTTPS Request (Port 1716)
MITM->>Filter : Forward Request
Filter->>Filter : Check Path Prefix
alt API Endpoint
Filter->>Logger : Capture Request
MITM->>CoreHub : Forward to Port 1717
CoreHub-->>MITM : API Response
MITM->>Logger : Capture Response
Logger-->>MITM : Log Entry
MITM-->>Client : Response with Logging
else Static Asset
Filter-->>MITM : Skip Capture
MITM->>CoreHub : Forward Without Logging
CoreHub-->>MITM : Response
MITM-->>Client : Direct Response
end
```

**Diagram sources**
- [capture_api.py:35-86](file://capture_api.py#L35-L86)
- [MITM_PROXY.md:136-157](file://MITM_PROXY.md#L136-L157)

**Section sources**
- [capture_api.py:1-90](file://capture_api.py#L1-L90)
- [start-mitm-capture.sh:1-51](file://start-mitm-capture.sh#L1-L51)
- [core-hub-mitm.sh:1-49](file://core-hub-mitm.sh#L1-L49)

## API Capture Framework

### Capture Logic Implementation

The API capture framework implements a comprehensive logging system that records complete request-response cycles with detailed metadata for each API interaction.

```mermaid
flowchart TD
Start([API Call Received]) --> CheckPath["Check Path Prefix"]
CheckPath --> IsAPI{"Is API Endpoint?"}
IsAPI --> |No| SkipCapture["Skip Capture"]
IsAPI --> |Yes| CreateEntry["Create Capture Entry"]
CreateEntry --> LogRequest["Log Request Details"]
LogRequest --> CaptureBody["Capture Request Body"]
CaptureBody --> StoreMetadata["Store in Flow Metadata"]
StoreMetadata --> ForwardToCoreHub["Forward to Core Hub"]
ForwardToCoreHub --> WaitResponse["Wait for Response"]
WaitResponse --> LogResponse["Log Response Details"]
LogResponse --> CaptureResponseBody["Capture Response Body"]
CaptureResponseBody --> AppendToLogs["Append to Log Array"]
AppendToLogs --> SaveToFile["Save to JSON File"]
SaveToFile --> PrintConsole["Print to Console"]
PrintConsole --> End([Complete])
SkipCapture --> End
```

**Diagram sources**
- [capture_api.py:35-86](file://capture_api.py#L35-L86)

### Data Structure Design

The capture framework employs a structured data model that ensures comprehensive logging of API interactions while maintaining flexibility for various payload types.

| Field | Type | Description | Capture Conditions |
|-------|------|-------------|-------------------|
| `timestamp` | string | ISO format timestamp | Always captured |
| `method` | string | HTTP method (GET, POST, etc.) | Always captured |
| `url` | string | Full request URL | Always captured |
| `path` | string | Request path only | Always captured |
| `headers` | dict | Request headers | Always captured |
| `request_body` | dict/string | Parsed JSON body | Valid JSON only |
| `request_body_raw` | string | Hex-encoded raw body | Invalid JSON only |
| `status_code` | int | HTTP status code | Response captured |
| `response_headers` | dict | Response headers | Response captured |
| `response_body` | dict/string | Parsed JSON response | Valid JSON only |
| `response_body_raw` | string | Hex-encoded raw response | Invalid JSON only |

**Section sources**
- [capture_api.py:41-79](file://capture_api.py#L41-L79)

## CLI Integration

### Authentication and Session Management

The CLI integration provides seamless authentication and session management for programmatic API interaction, mirroring the authentication flow captured during MITM sessions.

```mermaid
sequenceDiagram
participant User as "User Command"
participant CLI as "GlueSync CLI"
participant Auth as "Authentication Handler"
participant CoreHub as "Core Hub API"
participant Session as "Session Manager"
User->>CLI : Execute Command
CLI->>Auth : Initialize Client
Auth->>CoreHub : POST /authentication/login
CoreHub-->>Auth : {apiToken, user info}
Auth->>Session : Store Token
Session-->>Auth : Session Ready
Auth-->>CLI : Client with Auth
CLI->>CoreHub : API Request with Bearer Token
CoreHub-->>CLI : API Response
CLI-->>User : Formatted Output
```

**Diagram sources**
- [gluesync_cli.py:57-79](file://gluesync_cli.py#L57-L79)

### Command Structure and Routing

The CLI implements a sophisticated command routing system that supports both legacy and modern command patterns, enabling flexible API interaction for automation development.

| Command Pattern | Description | Usage Example |
|----------------|-------------|---------------|
| `gluesync-cli <action> <resource> [id] --flags` | Modern kubectl-style commands | `gluesync-cli get pipelines` |
| `gluesync-cli <resource> <action> [id] --flags` | Legacy command format | `gluesync-cli pipeline list` |
| `gluesync-cli <category> <action> [options]` | Resource-focused commands | `gluesync-cli entity start <id>` |

**Section sources**
- [gluesync_cli.py:574-743](file://gluesync_cli.py#L574-L743)
- [gluesync_cli_v2.py:67-111](file://gluesync_cli_v2.py#L67-L111)

## Containerization Strategy

### Multi-Stage Build Process

The containerization strategy implements a multi-stage approach supporting both production and development environments with optimized build processes and runtime configurations.

```mermaid
graph LR
subgraph "Development Environment"
DEV[Development Image<br/>Dockerfile.dev]
SRC[Source Code Volume]
HOT[Hot Reload<br/>Watchdog]
end
subgraph "Production Environment"
PROD[Production Image<br/>Dockerfile]
APP[Application Code]
REQ[Requirements]
end
subgraph "Build Process"
PY[Python 3.11 Base]
DEPS[System Dependencies]
PKGS[Python Packages]
end
PY --> DEPS
DEPS --> PKGS
PKGS --> DEV
PKGS --> PROD
DEV --> SRC
DEV --> HOT
PROD --> APP
PROD --> REQ
```

**Diagram sources**
- [Dockerfile:1-40](file://Dockerfile#L1-L40)
- [Dockerfile.dev:1-24](file://Dockerfile.dev#L1-L24)

### Container Orchestration

The framework utilizes Docker Compose for orchestrating multi-container deployments, supporting both standalone CLI operations and integrated development environments.

| Service | Purpose | Configuration | Volumes |
|---------|---------|---------------|---------|
| `gluesync-cli` | Production CLI container | Production Dockerfile | Config, Data, Scripts |
| `gluesync-cli-dev` | Development container | Development Dockerfile | Source Code, Environment |
| `networks` | Container networking | Bridge driver | Shared networking |

**Section sources**
- [docker-compose.yml:1-52](file://docker-compose.yml#L1-L52)
- [Makefile:17-112](file://Makefile#L17-L112)

## Deployment Configuration

### Environment Setup

The deployment configuration supports flexible environment variable management and externalized credential storage for secure operations across different environments.

```mermaid
flowchart TD
ConfigFile["config.json"] --> CoreHub["Core Hub Configuration"]
EnvFile[".env"] --> Credentials["Environment Variables"]
Makefile --> BuildProcess["Build Process"]
Dockerfile --> ImageBuild["Image Construction"]
CoreHub --> BaseURL["Base URL Configuration"]
CoreHub --> SSLVerify["SSL Verification"]
Credentials --> AdminUser["Admin Username"]
Credentials --> AdminPass["Admin Password"]
Credentials --> DBUsers["Database Credentials"]
BuildProcess --> ContainerImages["Container Images"]
ImageBuild --> ProductionImage["Production Image"]
ImageBuild --> DevImage["Development Image"]
```

**Diagram sources**
- [config.json:1-34](file://config.json#L1-L34)
- [Makefile:80-95](file://Makefile#L80-L95)

### Port Configuration Matrix

The framework implements a comprehensive port management system supporting multiple access patterns and operational modes.

| Port | Service | Purpose | Capture Mode | Direct Mode |
|------|---------|---------|--------------|-------------|
| **1716** | MITM Proxy | API capture and logging | ✅ Active | ❌ Inactive |
| **1717** | Core Hub | Direct API access | ❌ Inactive | ✅ Active |
| **8080** | Traefik | HTTP reverse proxy | ❌ Inactive | ✅ Active |
| **8443** | Traefik | HTTPS reverse proxy | ❌ Inactive | ✅ Active |
| **80** | TCP Proxy | HTTP forwarding | ❌ Inactive | ✅ Active |
| **443** | TCP Proxy | HTTPS forwarding | ❌ Inactive | ✅ Active |

**Section sources**
- [MITM_PROXY.md:69-82](file://MITM_PROXY.md#L69-L82)
- [scripts/tcp-proxy.py:1-72](file://scripts/tcp-proxy.py#L1-L72)

## Security Considerations

### Certificate Management

The MITM proxy framework implements secure certificate handling mechanisms to balance functionality with security requirements during API capture operations.

```mermaid
graph TB
subgraph "Certificate Authority"
CA[MITM Proxy CA Certificate]
CERT[Generated Client Certificates]
end
subgraph "Browser Trust"
ACCEPT[Accept Certificate]
INSTALL[Install CA Certificate]
BLOCK[Block Certificate]
end
subgraph "Security Impact"
TRUST[Browser Trust Established]
SECURITY[Security Compromised]
COMPROMISE[MITM Vulnerability]
end
CA --> CERT
CERT --> ACCEPT
CERT --> INSTALL
ACCEPT --> TRUST
INSTALL --> TRUST
ACCEPT --> SECURITY
INSTALL --> SECURITY
BLOCK --> COMPROMISE
```

**Diagram sources**
- [MITM_SETUP.md:184-184](file://MITM_SETUP.md#L184-L184)

### Sensitive Data Protection

The framework implements comprehensive measures to protect sensitive data captured during API interactions, including automatic sanitization and secure storage practices.

| Data Type | Protection Level | Storage Location | Retention Policy |
|-----------|------------------|------------------|------------------|
| Authentication Tokens | High | Encrypted JSON | Immediate Deletion |
| Database Credentials | Highest | Environment Variables | Never Stored |
| API Keys | High | External Secrets | Immediate Deletion |
| Request Bodies | Medium | JSON Logs | 7-day Rotation |
| Response Bodies | Medium | JSON Logs | 7-day Rotation |

**Section sources**
- [MITM_SETUP.md:238-250](file://MITM_SETUP.md#L238-L250)
- [MITM_PROXY.md:284-321](file://MITM_PROXY.md#L284-L321)

## Troubleshooting Guide

### Common Issues and Solutions

The framework provides comprehensive troubleshooting guidance for common operational issues encountered during MITM proxy setup and API capture operations.

| Issue Category | Symptoms | Diagnostic Steps | Resolution |
|----------------|----------|------------------|------------|
| **Port Conflicts** | Connection refused errors | `ss -tlnp \| grep :1716` | Kill conflicting process or change port |
| **Certificate Errors** | SSL handshake failures | Check browser certificate warnings | Accept certificate or install CA |
| **Capture Failures** | Empty log files | Verify traffic goes through 1716 | Check proxy configuration |
| **Authentication Issues** | 401/403 errors | Validate credentials in .env | Update environment variables |
| **Network Connectivity** | Connection timeouts | Test Core Hub accessibility | Verify network configuration |

### Performance Optimization

The framework includes performance monitoring and optimization guidelines for high-volume API capture scenarios.

**Section sources**
- [MITM_PROXY.md:284-321](file://MITM_PROXY.md#L284-L321)
- [MITM_SETUP.md:220-237](file://MITM_SETUP.md#L220-L237)

## Best Practices

### Operational Guidelines

The framework establishes comprehensive best practices for secure and efficient MITM proxy operations, ensuring reliable API capture and minimal impact on production systems.

```mermaid
mindmap
root((Best Practices))
Security
Certificate Management
Credential Protection
Log Sanitization
Performance
Port Separation
Traffic Filtering
Log Rotation
Operational
Incremental Capture
Environment Isolation
Monitoring
Development
API Documentation
Automation Scripts
Testing Protocols
```

### Capture Strategy Recommendations

The framework recommends strategic approaches to API capture that maximize information density while minimizing operational overhead and security risks.

**Section sources**
- [MITM_PROXY.md:324-331](file://MITM_PROXY.md#L324-L331)
- [README.md:396-414](file://README.md#L396-L414)

## Conclusion

The MITM Proxy and API Capture Framework provides a comprehensive solution for GlueSync API discovery, reverse engineering, and automation development. Through its sophisticated traffic interception mechanisms, structured logging system, and robust CLI integration, the framework enables developers to efficiently analyze API interactions and develop automated solutions.

The framework's multi-environment support, comprehensive security measures, and operational best practices ensure reliable deployment across diverse environments while maintaining optimal performance and security standards. By leveraging the captured API data and structured logging capabilities, development teams can accelerate automation development and integration projects with confidence in their understanding of GlueSync's API behavior.

The modular architecture and containerized deployment strategy facilitate easy integration into existing development workflows, while the comprehensive documentation and troubleshooting guidance ensure successful adoption and operation across different organizational contexts.