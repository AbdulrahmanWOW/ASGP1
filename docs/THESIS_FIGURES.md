# Thesis figure sources

The following Mermaid sources can be exported as SVG for the thesis.

## System boundary

```mermaid
flowchart LR
    U[User intent] --> A[Integrated AI agent]
    A --> S[ASGP SDK]
    S --> G[Governance gateway]
    G --> P[Policy and boundary checks]
    G --> R[Risk and security signals]
    G --> D{Decision}
    D -->|ALLOW| T[Controlled tool]
    D -->|ESCALATE| H[Human approval]
    D -->|BLOCK| X[Execution prevented]
    D --> Q[(Hash-chained audit)]
    Q --> UI[Dashboard]
```

## Evaluation design

```mermaid
flowchart TB
    DS[12 labeled scenarios] --> F[Full pipeline]
    DS --> A[Policy-only ablation]
    F --> M[Decision and latency metrics]
    A --> M
    M --> J[JSON and CSV]
    M --> R[Reviewable report]
```

Do not present the generated rates without the caption: “Results on the controlled ASGP lab dataset; not an estimate of real-world prevalence or generalization.”
