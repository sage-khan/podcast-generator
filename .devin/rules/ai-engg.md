---
trigger: always_on
---

# AI System Engineering Rules

## 0. Philosophy
- Favor simplicity until complexity is proven necessary.
- Optimize for clarity, reliability, and reversibility.
- Prioritize real constraints over theoretical scaling.

## 1. Baseline Architecture: Use the simplest production-ready stack that meets current requirements.
- One FastAPI server using vLLM for model execution.
- One PostgreSQL instance with pgvector, SQLite is acceptable for early stages.
- Include basic authentication, rate limiting, observability using OTEL, and CI/CD.
- Ensure full system debuggability, ensure rollbacks can be executed within 30 seconds.

## 2. Failure-First Learning: Understand common AI system failure modes before adopting complex scaling patterns.
- Study CUDA OOM incidents. Validate GPU memory behavior under load.
- Review embedding drift failures, token budget overruns, and prompt-injection breaches.
- Investigate real postmortems involving corrupted labels, failed retraining loops, silent data drift.
- Treat operational complexity as a primary risk factor. Simple systems fail more transparently.

## 3. Trade-Off Competency: Select tools based on contextual constraints, not on breadth of the ecosystem.
- Learn when high-overhead platforms like Kubeflow are beneficial, and when they introduce unnecessary delays.
- Compare alternatives such as Ray Serve, Triton, vLLM, TGI, Seldon, KServe, BentoML, choose only when a requirement demands it.
- Prefer background workers with Redis queues when they outperform Kafka, Flink, or Spark for the actual workload.
- Reduce operator count. Increase judgment quality.

## 4. Three-Horizon Design Strategy: Plan for incremental evolution across three time windows.

### Horizon 1. Immediate (Today): 
- Real users must receive responses in under 200 ms.
- Operating cost should remain under 50 dollars per month where possible.
- Reliability and observability must be sufficient for production on-call.

### Horizon 2. Mid-Term (1 Year)
- Support model replacement such as Llama 70B, Mixtral, Gemma, or fine-tunes.
- Avoid architecture choices that require rewriting core services during model swaps.

### Horizon 3. Long-Term (3 Years)
- Allow for scaling to 100k RPS, multi-modal workloads, or continuous fine-tuning.
- Architecture must evolve incrementally. Avoid designs that force large replatforming cycles.

## 5. Anti-Patterns
Avoid patterns that reduce development velocity or create brittle complexity.
- Do not introduce multi-service topologies without a verified scaling or isolation need.
- Do not build for hypothetical future traffic without evidence.
- Do not adopt enterprise platforms that slow iteration, cause unnecessary incidents, or lock the team into long migrations.

## 6. Principle-Driven Simplification
- The goal is not to minimize tools. The goal is to minimize unnecessary constraints.
- Simplicity is a performance strategy. Complexity is a liability unless required.