# Prompt Injection and Jailbreak Assessment

## Scope and outcome

The recommendation path accepts a user question and retrieved market/news text before constructing a Gemini prompt. Those inputs were previously interpolated directly into the prompt, allowing a malicious question or a poisoned article to compete with application instructions. A prompt-security boundary now evaluates and sanitizes both channels before model use, redacts credentials, labels retrieved evidence as untrusted data, and records a compact decision trail in the result.

## Findings and countermeasures

| Area | Previous weakness | Implemented control |
|---|---|---|
| Prompt injection | User query could contain instruction-like text. | High-severity override, role-tag, exfiltration, and encoding-evasion patterns are blocked before analysis. |
| Jailbreak attempts | No explicit detection for known jailbreak language. | Deterministic jailbreak/roleplay detection returns a safe refusal and `HOLD`, without sending attack text to the model. |
| Prompt leakage | The prompt did not prohibit disclosure and output was not screened. | The model contract forbids hidden-prompt/credential disclosure; output is credential-redacted and leakage/exfiltration attempts are blocked. |
| Instruction override | System and evidence were mixed in one plain-text prompt. | Trusted rules are declared first; market/news content is tagged `<untrusted-data>` and cannot supply instructions. |
| Prompt manipulation | No handling for impersonation or fake role instructions. | Administrator/developer impersonation patterns are classified and high-risk attempts are blocked. |
| Prompt robustness | No repeatable regression assessment. | Offline evaluator supports JSON suites and unit tests cover override, leakage, poisoned context, and ordinary queries. |

## Residual risk and operating guidance

Pattern detection can miss novel or obfuscated attacks and can occasionally flag unusual wording. It is therefore defense in depth, not an authorization boundary. Keep model credentials outside prompts, apply provider safety settings, restrict tools to least privilege, cap untrusted-context length, and review the `security` result metadata and audit events. Add new failed attack examples to `security_tests/student_1_prompt_security/` and run the evaluator in CI.
