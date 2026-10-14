# MCP Proxies and Middleware: A Comparative Analysis (team report, Sept 2026)

> Team report. Known issues (DESIGN.md §15): ASGP column in Table 5.1 overclaims; 'intent-based governance absent' is true only among MCP gateways; Bifrost section contradicts itself; Table 5.1 vs body mismatches (IBM/Microsoft audit, AIM-Intelligence missing); several figures are vendor-sourced; §2.2 'prevents' should be 'reduces'.

Alamein International University Faculty of Computer Science & Engineering A project submitted in partial fulfillment of the requirements for the BSc. degree

MCP Proxies and Middleware: A Comparative Analysis Security, Governance, and Intent-Based Agent Control by

Abdulrahman Supervised by September 2026

ABSTRACT The rapid adoption of the Model Context Protocol (MCP) — surpassing 97 million monthly downloads by mid-2026 — has created an urgent need for security and governance infrastructure. AI agents that communicate via MCP can access file systems, send emails, execute code, and call external APIs with minimal oversight. This report provides a comprehensive comparative analysis of existing MCP proxy and middleware solutions, evaluating each against six criteria: access control depth, authentication mechanisms, audit trail quality, performance overhead, deployment flexibility, and semantic governance capability. Five major open-source MCP gateways are analyzed in detail: Bifrost (Maxim AI), Docker MCP Gateway, IBM ContextForge, Microsoft MCP Gateway, and MCPProxy. Additionally, three security-focused middleware tools are examined: MCPShield, Haze518 Gateway, and AIMIntelligence Security Middleware. The analysis reveals that while infrastructure-level concerns such as authentication and routing are well-addressed by existing tools, semantic governance — the ability to verify whether an agent action aligns with the user's stated intent — remains entirely absent from all surveyed solutions. This gap is the primary motivation for the Agent Security Governance Platform (ASGP) proposed in the accompanying graduation project.

Chapter 1: Introduction 1.1 Background The Model Context Protocol (MCP), introduced by Anthropic in late 2024, defines a standard communication interface between AI agents and the tools they use. By establishing a unified JSON-RPC based protocol, MCP enables any MCP-compatible agent to interact with any MCPcompatible tool server without custom integration code. This standardization has accelerated agent deployment significantly — MCP now records 97 million monthly downloads and is supported by every major AI vendor including Anthropic, OpenAI, Google, and Microsoft. However, this rapid adoption has outpaced the development of security infrastructure. When Cisco announced dedicated MCP security tooling at RSA Conference 2026, the signal was unambiguous: MCP has moved from a developer convenience to production-critical infrastructure requiring formal governance. Without a proxy or middleware layer, every agent manages its own tool server connections and credentials independently — creating fragmented, unauditable, and insecure tool access at scale.

1.2 The Problem Three fundamental security failures arise when AI agents use MCP tools without a governance layer: ●

●

●

Prompt Injection: A malicious actor embeds hidden instructions inside content the agent retrieves — a webpage, an email, a file — causing the agent to execute unintended actions on behalf of the attacker. Unverified Agent Trust: In multi-agent pipelines, sub-agents cannot verify that instructions received from orchestrators have not been tampered with or injected in transit. Intent Drift: An agent session that begins legitimately can gradually expand its scope of actions beyond what the user authorized, with each individual step appearing acceptable while the overall trajectory constitutes a security violation.

Existing MCP proxy and gateway solutions address infrastructure concerns — authentication, routing, rate limiting — but none verify whether an agent's tool calls align with the user's stated intent at a semantic level. This report maps the existing landscape and identifies that gap precisely.

1.3 Objectives ● ● ● ● ●

Survey and categorize all significant open-source MCP proxy and middleware solutions available as of 2026. Evaluate each solution against a standardized set of six security and governance criteria. Identify specific capabilities that are absent from existing solutions. Provide a detailed pros and cons analysis for each tool to inform architectural decisions. Establish the research gap that motivates the ASGP graduation project.

1.4 Scope This report focuses exclusively on open-source MCP proxy and middleware tools. Commercial proprietary solutions (such as MCPX Enterprise or Zuplo's managed MCP gateway) are referenced for context but not analyzed in detail. The analysis covers tools available and documented as of September 2026.

Chapter 2: Background and Definitions 2.1 What is MCP? The Model Context Protocol is a JSON-RPC 2.0 based standard defining three participant roles: ●

MCP Host: An application that embeds an AI model and manages MCP connections (e.g., Claude Desktop, VS Code with Copilot, Cursor). MCP Client: The component within the host that initiates connections to MCP servers and calls their tools. MCP Server: A program that exposes tools, resources, and prompts to MCP clients through a standardized interface.

● ●

Communication uses two transport mechanisms: stdio (standard input/output, used by Claude Desktop and local tools) and Streamable HTTP (used by remote and cloud-deployed tool servers). Every tool call follows the same JSON-RPC structure: Field

Value

Description

jsonrpc

"2.0"

Protocol version

method

"tools/call"

Always this for tool invocation

params.name

"send_email"

The tool being called

params.arguments

{ "to": "...", "body": "..." }

Tool-specific parameters

id

"1"

Request correlation ID

2.2 Why a Proxy or Gateway? Without a proxy, every agent instance manages its own connection to every tool server. This means credentials are scattered across agent deployments, there is no central audit point, and policy enforcement must be duplicated in every agent. A proxy or gateway centralizes these concerns: it sits between agents and tool servers, authenticates requests, enforces access control policies, logs every tool invocation, and optionally transforms requests and responses. The proxy approach offers an additional security benefit that is critical for agent systems: the agent itself need not know that the proxy exists. From the agent's perspective, it is communicating directly with a tool server. This architectural invisibility prevents prompt injection attacks from containing instructions specifically targeting the security layer.

2.3 Evaluation Criteria Each tool in this report is evaluated against six criteria: Criterion

Definition

Access Control Depth

Can the gateway enforce permissions at the server level, tool level, and parameter level?

Authentication

Support for OAuth 2.0/2.1, API keys, enterprise identity providers (Okta, Entra ID).

Audit Trail Quality

Immutability, queryability, and compliance readiness of logs (SOC 2, HIPAA, GDPR).

Performance Overhead

Latency added per tool call under production load.

Deployment Flexibility

Supported transports, deployment targets (Docker, Kubernetes, binary), in-VPC operation.

Semantic Governance

Whether the tool verifies that agent actions align with the user's stated intent — not just identity-based access control.

Chapter 3: MCP Infrastructure Gateways This chapter covers the five major open-source MCP gateway solutions that address infrastructure-level concerns: routing, authentication, access control, and observability.

3.1 Bifrost (Maxim AI) Property

Detail

Developer

Maxim AI (H3 Labs Inc.)

License

Apache 2.0

Language

Go

Deployment

Binary, Docker, Kubernetes

Performance

11 microseconds overhead per request at 5,000 RPS sustained

Transports

STDIO, HTTP, SSE

Overview Bifrost is the most comprehensive open-source MCP gateway currently available. It functions simultaneously as both an MCP client (connecting to upstream tool servers) and an MCP server (exposing aggregated tools to downstream agents through a single /mcp endpoint). This dual role makes it the only tool in this analysis capable of acting as a true protocol-level proxy rather than a simple pass-through router. Bifrost is unique in also handling LLM routing — it manages model requests across 20 or more LLM providers with automatic failover and load balancing alongside its MCP gateway functionality. This eliminates the need for teams to maintain two separate infrastructure components for LLM traffic and tool traffic. Key Capabilities ● Agent Mode: Autonomous tool execution with configurable auto-approval policies, enabling agents to complete multi-step workflows without per-step human intervention. ● Code Mode: Instead of calling tools directly, Bifrost's Code Mode instructs the AI to write Python to orchestrate multiple tools in a single execution. This reduces token consumption by approximately 50 percent and cuts latency by approximately 40 percent compared to sequential tool calls. ● OAuth 2.0 Authentication: Full OAuth flow with PKCE and automatic token refresh for connecting to authenticated MCP servers. ● Tool Filtering Per Virtual Key: Control exactly which MCP tools each team, consumer, or workflow can access, enforced at the gateway level. ● Vault Integration: Credentials managed via HashiCorp Vault, AWS Secrets Manager, Google Secret Manager, and Azure Key Vault. ● Federated Authentication: Transform existing internal REST and gRPC APIs into MCP-compatible tool definitions without writing new server code. Detailed Pros ✔ Lowest latency in the category: 11 microseconds per request at 5,000 RPS makes it suitable for high-throughput agent workflows where every millisecond counts. ✔ Only gateway that handles both LLM routing and MCP tool orchestration from a single binary — significantly simplifies infrastructure. ✔ Production-grade credential management through integration with enterprise secret stores (Vault, AWS Secrets Manager). ✔ OAuth 2.0 with PKCE provides enterprise-grade authentication that satisfies most compliance requirements out of the box.

✔ Code Mode's token reduction capability makes it economically significant for high-volume deployments. ✔ Apache 2.0 license — fully open, permissive, suitable for academic research and commercial use without restriction. ✔ Active development and community support; SOC 2, GDPR, ISO 27001, and HIPAA compliance documentation available. Detailed Cons ✖ No semantic governance: Bifrost enforces access control based on agent identity and tool name — it has no concept of whether a tool call makes sense for the user's current task. An agent with access to send_email can use it at any point, even when the user only asked for a file summary. ✖ No intent anchoring: There is no mechanism to capture what the user originally asked for and enforce that subsequent tool calls align with that intent. ✖ No prompt injection detection: Bifrost does not scan retrieved content for hidden instructions before returning it to the agent. ✖ No cryptographic signing chain: Agent instructions are not signed, meaning compromised agents can issue arbitrary tool calls within their access control boundaries without detection. ✖ Does not perform protocol translation — cannot convert REST or gRPC services into MCP tools without additional tooling. ✖ Code Mode reduces transparency — when an AI writes and executes Python to orchestrate tools, the individual tool calls are harder to audit than direct MCP calls. ✖ Enterprise features (Vault integration, SOC 2 compliance) are well-documented but the selfhosted open-source version lacks the managed support of the enterprise tier.

3.2 Docker MCP Gateway Property

Detail

Developer

Docker Inc.

License

Apache 2.0

Language

Go

Deployment

Docker Desktop, Docker Engine binary

Performance

Container startup overhead per server; runtime overhead not published

Transports

STDIO (through container), HTTP

Overview Docker's MCP Gateway takes a fundamentally different approach from other gateways: rather than routing requests to running tool servers, it manages the full lifecycle of MCP servers as isolated Docker containers. When an agent requests a tool, the gateway starts the appropriate container if it is not already running, injects credentials securely, and proxies the request. When the request is complete, containers can be paused or stopped to free resources. This container-per-server model provides the strongest isolation guarantees of any tool in this analysis. Each tool server runs with its own filesystem, network namespace, and process space. A compromised tool server cannot directly access resources belonging to other tool servers. Detailed Pros ✔ Strongest isolation model available: each MCP server runs in a fully isolated Docker container, limiting blast radius if a tool server is compromised or exploited. ✔ Cryptographically signed container images ensure tool servers have not been tampered with between download and execution.

✔ Built-in secrets injection means credentials are never stored in the agent's environment — they are injected at container start time and scoped to that container's lifetime. ✔ Native Docker Desktop integration provides zero-friction local development experience — most developers already have Docker Desktop installed. ✔ Automatic container lifecycle management eliminates the need to manually start and stop tool servers. ✔ Apache 2.0 license, fully open source. Detailed Cons ✖ Container startup overhead: the first call to a tool server that is not already running incurs full container startup latency — typically 500ms to 2 seconds depending on image size. This is unacceptable for latency-sensitive agent workflows. ✖ Designed primarily for developer-local and container-native environments — not suitable for multi-tenant enterprise governance or team-wide policy enforcement without significant additional tooling. ✖ No LLM routing: teams running LLM traffic and MCP tool traffic need a separate AI gateway alongside Docker MCP Gateway. ✖ No semantic governance, intent anchoring, or prompt injection detection — the same fundamental gap as all other infrastructure gateways. ✖ Cross-team access control and organizational policy enforcement require building additional tooling on top of the base gateway. ✖ No support for tool-level RBAC — access control is at the server level only. ✖ Audit logging is partial — container-level logs are available but there is no unified immutable audit trail across all tool invocations.

3.3 IBM ContextForge (MCP Context Forge) Property

Detail

Developer

IBM Research

License

Apache 2.0

Language

Python

Deployment

PyPI, Docker, Kubernetes (multi-cluster)

Performance

Higher per-request overhead than Go-based alternatives due to Python runtime

Transports

MCP, REST, gRPC (bidirectional translation)

Overview IBM ContextForge's distinguishing feature is protocol translation: it can convert existing REST and gRPC services into MCP-compatible tool definitions, allowing organizations to expose their existing internal APIs to AI agents without rewriting them as MCP servers. This is a significant practical advantage for large enterprises with extensive existing API infrastructure. ContextForge also provides dynamic tool discovery — agents can query it to find available tools without needing static configuration — and OpenTelemetry-based observability that integrates with existing monitoring infrastructure (Phoenix, Jaeger, Zipkin). Detailed Pros ✔ Protocol translation is unique in this category: existing REST and gRPC APIs become MCP-accessible without rewriting them as MCP servers — critical for large enterprises with extensive legacy API infrastructure. ✔ Dynamic tool discovery allows agents to find available tools at runtime rather than requiring static configuration.

✔ 40 or more plugins for additional transports and integrations provide the most extensible architecture in this comparison. ✔ OpenTelemetry integration with Phoenix, Jaeger, and Zipkin means observability plugs into existing enterprise monitoring stacks. ✔ Redis-backed caching for multi-cluster federation enables horizontal scaling across data centers. ✔ Admin UI for real-time configuration and log monitoring without needing CLI access. ✔ Built-in retry and rate limiting reduce the operational burden of managing unreliable upstream tool servers. Detailed Cons ✖ Python runtime produces higher per-request latency than Go-based alternatives (Bifrost, Docker, Microsoft). In high-throughput scenarios this overhead compounds significantly. ✖ Enterprise governance features — RBAC, SSO integration, immutable audit trails — are still maturing compared to more established options. IBM acknowledges these are in active development. ✖ Newer project than most others: less production-hardened, smaller community, fewer documented deployments at scale. ✖ No semantic governance, intent anchoring, or prompt injection detection. ✖ No LLM routing — requires separate AI gateway for model traffic. ✖ The breadth of plugin support adds complexity: teams must understand which plugins to enable and how to configure them correctly for their environment.

3.4 Microsoft MCP Gateway Property

Detail

Developer

Microsoft

License

MIT

Language

Go

Deployment

Kubernetes only

Performance

Not published

Transports

HTTP, SSE

Overview Microsoft's MCP Gateway is a reverse proxy and management layer designed specifically for Kubernetes environments and Azure infrastructure. Its architectural innovation is the concept of Adapters — logical representations of MCP servers managed under a unified control plane — and a Tool Gateway Router that acts as an intelligent routing agent, directing tool execution requests to the appropriate registered server based on tool definitions. The gateway introduces session-aware stateful routing: it ensures that all requests carrying the same session ID consistently reach the same MCP server instance. This is critical for stateful tool servers that maintain context between calls within a conversation. Detailed Pros ✔ Session-aware stateful routing is the only gateway in this analysis to address the problem of stateful MCP servers — ensuring conversation continuity for tools that maintain context between calls. ✔ Azure Entra ID (formerly AAD) integration provides enterprise-grade authentication that directly satisfies Microsoft ecosystem compliance requirements. ✔ Tool Gateway Router provides intelligent routing based on tool definitions rather than simple URL mapping — useful when multiple servers expose overlapping tool names.

✔ MIT license — more permissive than Apache 2.0, allowing integration without license notice requirements. ✔ Go implementation provides the same performance characteristics as Bifrost and Docker, with low per-request overhead. Detailed Cons ✖ Kubernetes-only deployment: not usable for individual developers, small teams without Kubernetes infrastructure, or local development environments without significant setup overhead. ✖ Azure ecosystem lock-in: the authentication and RBAC model is tightly coupled to Azure Entra ID. Teams not using Azure face significant friction adapting it to other identity providers. ✖ Not a general-purpose MCP gateway — explicitly positioned for Microsoft/Azure environments. Using it outside that context requires forking and significant modification. ✖ No LLM routing, no semantic governance, no intent anchoring, no prompt injection detection. ✖ Performance overhead not published — teams cannot evaluate latency impact before adopting it. ✖ No tool-level RBAC independent of Kubernetes RBAC — access control model is tightly coupled to Kubernetes primitives.

3.5 MCPProxy (mcpproxy-go) Property

Detail

Developer

smart-mcp-proxy (open source)

License

Open source

Language

Go

Deployment

Single binary — 30-second setup

Performance

Low overhead; exact figures not published

Transports

STDIO, HTTP

Overview MCPProxy prioritizes developer simplicity above all other concerns. Its stated goal is to remain a single binary that can be downloaded and running in 30 seconds. It provides BM25-based tool discovery — allowing agents to find relevant tools by semantic similarity to a query rather than exact name match — alongside a quarantine security feature that holds suspicious tool calls for review before execution. MCPProxy's roadmap includes expanding its quarantine rules to cover the full OWASP MCP Top 10, adding OS-level sandboxing via Linux Landlock, and publishing a benchmark suite for evaluating MCP server tool-use capabilities. Detailed Pros ✔ Exceptional developer experience: single binary, no configuration required to get started, 30-second time-to-running for individual developers. ✔ BM25-based tool discovery is a meaningful usability improvement over exact-name matching — particularly useful when multiple tool servers expose similar functionality under different names. ✔ Quarantine security feature provides a basic human-in-the-loop mechanism for suspicious tool calls — the closest any infrastructure gateway comes to escalation functionality. ✔ Token savings through tool discovery consolidation reduce LLM API costs. ✔ Lean architecture means minimal attack surface and straightforward security auditing.

Detailed Cons ✖ No enterprise governance: no RBAC, no SSO integration, no audit logging suitable for compliance purposes. ✖ No authentication support — tool servers are accessible to any caller without credential verification. ✖ Quarantine feature is basic: it holds suspicious calls but provides no semantic analysis of why a call is suspicious or whether it aligns with the user's intent. ✖ BM25 tool discovery is lexical similarity, not semantic similarity — tools with different naming conventions for the same concept may not be discovered correctly. ✖ No cryptographic signing, no intent anchoring, no prompt injection detection. ✖ Not suitable for production multi-agent deployments or team environments — designed for individual developer use.

Chapter 4: MCP Security Middleware This chapter covers three tools specifically positioned as security layers for MCP, as distinct from general-purpose gateways. These tools focus on blocking dangerous calls, detecting secret leakage, and enforcing deny-by-default policies.

4.1 MCPShield Property

Detail

Developer

ferrierepete (open source)

License

Open source

Language

Not specified

Deployment

stdio proxy — transparent interception

Key Feature

Transparent stdio proxy blocking dangerous tool calls and scanning for secret leakage

Overview MCPShield operates as a transparent stdio proxy — it intercepts the stdio stream between the agent and tool servers without requiring any configuration change in either. It blocks dangerous tool calls based on a predefined rule set, scans all JSON-RPC messages for secret leakage (API keys, tokens, passwords appearing in tool call parameters), and logs every message for forensic review. Detailed Pros ✔ Zero-configuration deployment: operates transparently on the stdio stream without any changes to the agent or tool servers. ✔ Secret leakage detection is a practically useful security feature — prevents agents from accidentally including credentials in tool call parameters where they could be logged or exfiltrated. ✔ Complete JSON-RPC message logging provides full visibility into all tool calls for forensic analysis. ✔ Dangerous tool call blocking provides a basic safety net against obviously harmful operations. Detailed Cons ✖ Rule-based blocking only: MCPShield cannot understand context. A call to delete_file may be legitimate during a cleanup task or malicious during a summarization task — MCPShield blocks based on the tool name alone, not the task context. ✖ High false positive rate: rule-based blocking of broadly dangerous tools (delete, execute, send) will block legitimate uses, degrading agent productivity. ✖ No semantic analysis, no intent anchoring, no alignment scoring. ✖ stdio only: does not support HTTP or SSE transports, limiting applicability to local tool servers. ✖ No authentication, RBAC, or audit trail suitable for compliance.

4.2 Haze518 Gateway Property

Detail

Developer

haze518 (open source)

License

Open source

Key Features

Deny-by-default policy, argument validation, rate limiting, tamper-evident audit logging

Released

March 13, 2026

Overview Haze518 Gateway is notable for its deny-by-default security posture — all tool calls are blocked unless explicitly permitted by policy. This is the most secure default of any tool in this analysis. It also implements argument validation (verifying that tool call parameters meet expected formats and ranges before forwarding), rate limiting, and tamper-evident audit logging using hash chaining — the same approach used by ASGP's audit layer. Detailed Pros ✔ Deny-by-default posture is the most security-conservative approach available — nothing executes without explicit policy approval. This eliminates the entire class of agent overprivilege vulnerabilities. ✔ Argument validation before forwarding prevents malformed inputs from reaching tool servers — useful both for security and reliability. ✔ Tamper-evident audit logging with hash chaining is a sophisticated feature rarely seen in open-source tools — it provides mathematically verifiable evidence that logs have not been altered after the fact. ✔ Rate limiting provides a basic defense against agent runaway behavior or resource exhaustion. Detailed Cons ✖ No semantic governance: the deny-by-default policy is configured by tool name and argument type — not by user intent. A user who says 'summarize my emails' can still have an agent send_email if that tool is in the allowlist. ✖ Policy configuration requires manual specification of every permitted tool and argument pattern — high operational overhead for teams with many tools or frequently changing workflows. ✖ No intent anchoring: there is no concept of a session-scoped user intent that constrains which policies apply to a given task. ✖ No prompt injection detection in retrieved content. ✖ Relatively new and small community — limited production deployment evidence.

4.3 AIM-Intelligence Security Middleware Property

Detail

Developer

AIM-Intelligence

Downloads

1.1k (as of mid-2026)

Key Feature

Security middleware guarding MCP implementations against unauthorized access, data leakage, and malicious tool calls

Released

August 20, 2025

Overview AIM-Intelligence provides a security middleware layer that guards MCP implementations against unauthorized access, data leakage, and malicious tool calls. It occupies a middle ground between the infrastructure gateways (Bifrost, Docker) and the more specialized security tools (MCPShield, Haze518), providing basic security hardening without the full governance capabilities of enterprise-grade gateways. Detailed Pros ✔ Addresses data leakage prevention — scans tool call parameters for sensitive data patterns before forwarding. ✔ Unauthorized access prevention provides basic authentication enforcement. ✔ Malicious tool call detection provides a rule-based safety layer.

Detailed Cons ✖ Limited documentation — implementation details and performance characteristics are not publicly available, making evaluation difficult. ✖ Relatively low adoption (1.1k downloads) suggests limited production validation. ✖ No semantic governance, no intent anchoring, no alignment scoring. ✖ No cryptographic signing chain.

Chapter 5: Comparative Analysis 5.1 Feature Comparison Matrix Table 5.1 compares all eight tools across the six evaluation criteria established in Chapter 2, plus four additional ASGP-specific capabilities. Capability

Bifrost

Docker

IBM CF

Microsoft

MCPProxy

MCPShield

Haze518

ASGP

MCP proxy / intercept

✔

✔

✔

✔

✔

✔

✔

✖

Tool-level RBAC

✔

✖

✖

✔

✖

✖

✖

✔

OAuth 2.0 Auth

✔

✖

✖

✔

✖

✖

✖

✖

Tamper-evident audit

✔

✖

✔

✔

✖

✖

✔

✔

Secret leakage detect

✖

✖

✖

✖

✖

✔

✖

✖

Deny-by-default

✖

✖

✖

✖

✖

✖

✔

✖

User intent anchoring

✖

✖

✖

✖

✖

✖

✖

✔

Semantic alignment scoring

✖

✖

✖

✖

✖

✖

✖

✔

Cryptographic signing chain

✖

✖

✖

✖

✖

✖

✖

✔

Prompt injection detection

✖

✖

✖

✖

✖

✖

✖

✔

Human-in-loop escalation

✖

✖

✖

✖

✔

✖

✖

✔

Plain language explanation

✖

✖

✖

✖

✖

✖

✖

✔

Open source

✔

✔

✔

✔

✔

✔

✔

✔

Table 5.1: Feature comparison matrix. ✔ = capability present, ✖ = capability absent. ASGP uses SDK approach (proxy is planned future work).

5.2 The Fundamental Gap The comparison matrix reveals a clear and consistent pattern: every existing MCP proxy and middleware solution — regardless of sophistication, maturity, or language — governs agent behavior based on identity. Access control is enforced by answering the question: who is this agent, and which tools does it have permission to use? None of them answer the equally important question: does what this agent is doing right now make sense given what the user asked for? This distinction is critical. Consider the following scenario: a user asks their agent to summarize their emails. The agent has permission to use send_email — the organization has granted it this permission because sometimes agents do need to send emails. A prompt injection in one of those emails hijacks the agent and causes it to call send_email to forward all emails to an external attacker.

Every infrastructure gateway in this analysis — Bifrost, Docker, IBM, Microsoft, MCPProxy — would allow this call. The agent is authenticated. The tool is permitted. The call structure is valid. None of these systems ask: did the user ask for emails to be sent? The answer is no — and that answer would block the attack. This is the semantic governance gap. It is not a gap in access control, authentication, or audit logging. It is a gap in intent verification — and it is the gap that ASGP is designed to fill.

5.3 Positioning ASGP ASGP does not compete with Bifrost or Docker MCP Gateway. It complements them. ASGP's governance engine — intent anchoring, semantic alignment scoring, cryptographic signing chain, prompt injection detection — can run as a middleware layer in front of any existing MCP gateway. The ideal architecture combines: ● ●

A transport-layer gateway (Bifrost for high performance, Docker for isolation, MCPProxy for simplicity) handling authentication, routing, and access control. ASGP's semantic governance layer sitting between the gateway and tool servers, adding intent verification that no existing gateway provides.

In this architecture, Bifrost solves the infrastructure problems (11 microsecond overhead, OAuth, Vault integration) and ASGP solves the semantic governance problem (does this call align with the user's intent?). Neither duplicates the other's work.

Chapter 6: Conclusion This report has surveyed eight open-source MCP proxy and middleware solutions across two categories: infrastructure gateways (Bifrost, Docker MCP Gateway, IBM ContextForge, Microsoft MCP Gateway, MCPProxy) and security middleware (MCPShield, Haze518 Gateway, AIM-Intelligence Security Middleware). The survey finds that the infrastructure gateway category is well-served by existing tools, with Bifrost representing the current state of the art: 11 microsecond per-request overhead, OAuth 2.0 authentication, tool-level RBAC, vault credential management, and Apache 2.0 licensing. Teams requiring container isolation will find Docker MCP Gateway most appropriate. Teams embedded in Azure will find Microsoft MCP Gateway the natural fit. Teams prioritizing developer simplicity will find MCPProxy the fastest path to running. The security middleware category is less mature. MCPShield provides useful secret leakage detection. Haze518 provides a valuable deny-by-default posture with tamper-evident logging. Neither, however, addresses semantic governance. Across all eight tools, the analysis identifies a consistent and complete absence of intent-based governance: no tool captures what the user asked for, verifies that subsequent agent actions align with that intent, or distinguishes between a legitimate agent action and an identical action caused by prompt injection. This gap represents both the primary security risk in current MCP deployments and the primary research contribution of the ASGP graduation project. Future work in this space should examine the feasibility of integrating semantic governance layers with existing infrastructure gateways — particularly the integration of ASGP's governance engine with Bifrost as a transport layer — and the development of standardized benchmarks for evaluating semantic alignment accuracy across diverse agent task domains.

References [1] [2] [3] [4] [5] [6]

K. Paul, "Best Open Source MCP Gateways in 2026," Maxim AI, Apr. 2026. [Online]. Available: https://www.getmaxim.ai/articles/best-open-source-mcp-gateways-in-2026/ Algis, "The MCP Gateway Landscape in 2026: Where MCPProxy Fits," DEV Community, Mar. 2026. [Online]. Available: https://dev.to/algis/the-mcp-gateway-landscape-in-2026-where-mcpproxy-fits-mjk "Best Open Source MCP Gateways 2026," Lunar.dev, May 2026. [Online]. Available: https://www.lunar.dev/post/the-best-open-source-mcp-gateways-in-2026 Anthropic, "Model Context Protocol: Introduction," 2024. [Online]. Available: https://modelcontextprotocol.io/introduction OWASP, "OWASP Top 10 for Large Language Model Applications 2025," 2025. [Online]. Available: https://owasp.org/www-project-top-10-for-large-language-model-applications/ "MCP Security Gateway," PulseMCP, 2026. [Online]. Available: https://www.pulsemcp.com/servers/mcp-security-gateway
