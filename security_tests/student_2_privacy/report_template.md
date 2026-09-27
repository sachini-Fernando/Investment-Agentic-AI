# Individual Vulnerability Assessment Report

**Student:** [name and index]  
**Specialization:** Student 2 - Privacy and Data Leakage Assessment  
**System:** InvestSage Agentic AI  
**Assessment date:** [date]  
**Environment:** Windows, Python [version], repository commit [hash]

## 1. Executive Summary

State the objective, test count, test environment, and the most important privacy findings. Do not claim a behavior is a vulnerability until it has evidence.

## 2. Scope of Testing

### In scope

- Streamlit authentication and session state.
- Local JSON user/history storage.
- MongoDB history and analysis persistence paths, where configured.
- Audit logging and secret resolution.
- Access control, retention, deletion, and data minimization.

### Out of scope

- Attacks against third-party providers.
- Real user data, real credentials, production databases, and denial of service.
- Source-code redesign or remediation implementation.

## 3. Methodology

Describe black-box UI tests plus white-box local verification. Explain that all inputs were synthetic and each result was recorded as expected behavior, actual behavior, evidence, observation, and conclusion. List Python, pytest, Streamlit, PowerShell, and browser developer tools used.

## 4. Test Cases Performed

Use the 15 entries in `privacy_test_cases.json`. For each test include:

- Test ID and objective
- Input/attack scenario
- Expected result
- Actual result
- Evidence filename
- Outcome: Pass, Fail, or Observation
- Privacy implication

## 5. Vulnerabilities Identified

For every confirmed issue:

### [V-01] [short title]

**Affected component:** [file/function/UI]  
**Evidence:** [test ID and evidence filename]  
**Description:** [what happens]  
**Impact:** [who can access what]  
**Likelihood:** [Low/Medium/High and technical reason]  
**Severity/risk:** [Critical/High/Medium/Low/Informational and justification]  
**Technical explanation:** [data flow and missing control]  
**Recommended mitigation:** [specific practical fix]

## 6. Risk Assessment

Complete `findings/risk_register.csv`. Define impact and likelihood scales and show a matrix. Distinguish exposed metadata from passwords, and a local development fallback from a remotely exploitable issue.

## 7. Mitigation Strategies

Cover deny-by-default history access, trusted server-side identity, strict cross-user authorization, encryption at rest, secret-manager use, log redaction, retention/deletion/export controls, secure session invalidation, default-credential removal, and access monitoring.

## 8. Reflection

Discuss challenges, lessons learned, limitations of synthetic testing, and what you would test next with an authorized staging database.

## 9. Viva Preparation

Be ready to explain why each test was selected, which tests found a weakness, how evidence proves the claim, why each risk level is justified, and why each mitigation addresses the controlling data-flow boundary.