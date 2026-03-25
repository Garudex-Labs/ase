<div align="center">

<picture>

  <source media="(prefers-color-scheme: dark)" srcset="./public/dark_scm.png">
  <source media="(prefers-color-scheme: light)" srcset="./public/light_scm.png">
  <img alt="SCM Logo" src="./public/dark_scm.png" width="250">

</picture>



# SCM (Secure Contract Machine)



![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)
![Status](https://img.shields.io/badge/Status-Thesis%20%26%20Prototyping-orange.svg?style=flat-square)


---

</div>

# SCM (Secure Contract Machine)

> ⚠️ **Notice:** This project is currently under active thesis research and prototyping. It is **not ready for production use**.

**SCM (Secure Contract Machine)** is a containerised runtime designed specifically for the era of multi-agent coordination. It provides a secure, deterministic environment that enables AI agents to negotiate security policies, execute constrained actions, and generate cryptographically verifiable audit records.

## 👾 Thesis & Motivation

SCM is developed to address a core problem in multi-agent environments: secure coordination under mutual distrust. As AI agents increasingly operate across different organizations and access sensitive systems, they must establish shared operational policies and provide auditable records that these policies were followed.

Rather than acting as a framework that agents are built upon, SCM operates as infrastructure, an isolated runtime middleware layer that independent agents call into. The project relies on production-ready open standards, including Z3 for satisfiability checking, ProVerif for symbolic protocol verification, and Halo2 PLONK for ZK transcript authenticity.

## 👾 Implementation Guide

SCM encapsulates four sequential components inside a single runtime container. External agents interact with this internal pipeline through standardized integration interfaces.

### 1. The Core Pipeline

* **Policy Capture:** Transforms an agent's requirements (natural language, JSON, or DSL) into a machine-checkable Formal Security Policy (FSP). This FSP is checked for internal consistency by Z3 and signed by the agent.

* **Negotiation Engine:** Takes the FSPs of participating agents and produces a Shared Coordination Policy (SCP). It runs a Z3-backed Pre-Negotiation Compatibility Check (PNCC) to ensure the hard predicates of all agents are jointly satisfiable before bargaining begins.

* **Security Reasoner:** Maps the negotiated SCP to a formally verified cryptographic protocol specification. It acts as an execution guard for post-negotiation agent actions, verifying contract tokens before allowing capabilities to be exercised.

* **Audit and Reporting:** Generates a dual-signed Merkle transcript of the execution trace and a Halo2 PLONK ZK-SNARK proof of authenticity.

### 2. Adaptive Execution Strategy

The SCM runtime automatically determines the required verification depth for each session, eliminating manual mode selection. Sessions are routed to one of four tiers based on the SCP's novelty and risk:

* **Cached Tier:** Executes in under 100 milliseconds if the SCP fingerprint matches a verified entry in the cache.

* **Library Tier:** Executes in under 500 milliseconds by applying a pre-verified protocol template retrieved via BGE-M3 dense embedding cosine similarity.

* **Rule Tier:** Executes in under 2 seconds for known-safe patterns resolved by a deterministic rule engine.

* **Synthesis Tier:** Targets a 60-second latency for novel or high-stakes sessions, utilizing live ProVerif verification and ZK proof generation.

### 3. Integration & Deployment

* **Integration Surfaces:** Agents can connect to SCM via a REST API (ideal for language-neutral deployments) or an MCP plugin (designed for LLM-based agent frameworks).

* **Deployment Modes:** * *Gateway Mode:* The production default, where a shared SCM instance sits at the edge of an agent deployment.

* *Sidecar Mode:* Designed for high-assurance, cross-organization environments, deploying an SCM instance alongside each agent as a Kubernetes sidecar.

---

## 👾 "Powered by SCM" Label

If you are building experimental integrations with SCM and want to showcase it, use our official label in your `README.md`.
> *(Note: Copy and paste the HTML below to display the dynamically adapting label.)* 

```html
<a href="https://github.com/Garudex-Labs/scm" target="_blank" style="text-decoration:none;">
  <img src="https://img.shields.io/badge/Powered%20By-0056b3?style=for-the-badge" alt="Powered By" height="30" align="absmiddle" style="margin-right: 6px;"/>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_light.png">
    <img alt="SCM Logo" src="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_light.png" height="30" align="absmiddle">
  </picture>
</a>
```

**Demo of the label:**

<a href="https://github.com/Garudex-Labs/scm" target="_blank" style="text-decoration:none;"><img src="https://img.shields.io/badge/Powered%20By-0056b3?style=for-the-badge" alt="Powered By" height="30" align="absmiddle" style="margin-right: 6px;"/><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_dark.png"><source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_light.png"><img alt="SCM Logo" src="https://raw.githubusercontent.com/Garudex-Labs/scm/main/public/scm_logo_light.png" height="30" align="absmiddle"></picture></a>

---

Project by Garudex Labs.

- Repository: https://github.com/Garudex-Labs
- Support: open an issue on the repository for questions or contributions.

© Garudex Labs 2026