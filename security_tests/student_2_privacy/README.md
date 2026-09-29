# Student 2: Privacy and Data Leakage Assessment

This folder is the evidence workspace for the individual Student 2 assessment. It is separate from application code.

## Folder contents

```text
student_2_privacy/
  README.md
  privacy_test_cases.json
  test_privacy_assessment.py
  report_template.md
  evidence/README.md
  findings/risk_register.csv

src/security/student_2_privacy/
   __init__.py
   privacy_controls.py
   privacy_evaluator.py
```

The `security_tests` folder contains assessment inputs, executable assessment
tests, evidence, and report material. The `src/security` folder contains
reusable privacy-security code, following the same pattern as Student 1's
prompt-security implementation.

## Reusable chat privacy interface

`src.security.student_2_privacy.inspect_privacy` accepts user input, caller
identity, history, generated response, and audit details. It returns a
JSON-compatible dictionary with `allowed`, `status`, `reason`, `findings`, and
sanitized values.

```python
from src.security.student_2_privacy import inspect_privacy

before_analysis = inspect_privacy(
   user_input=user_query,
   user_id=current_user_id,
   history=history_records,
)
if not before_analysis["allowed"]:
   # Do not call the analysis workflow; show before_analysis["reason"] instead.
   return before_analysis

# Run the existing analysis workflow here.

after_analysis = inspect_privacy(
   user_input=user_query,
   user_id=current_user_id,
   generated_response=generated_answer,
   audit_details={"ticker": ticker},
)
safe_answer = after_analysis["safe_output"]
safe_audit_details = after_analysis["safe_audit_details"]
```

The current Streamlit chat flow now calls this adapter before analysis and
after response generation. The integration is limited to the existing chat
boundary; the agentic workflow and persistence architecture are unchanged.

## Step-by-step execution

1. Open PowerShell at the repository root and activate the environment:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

2. Install requirements if needed:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Run only the privacy assessment. It uses temporary files, synthetic users, and canary strings:

   ```powershell
   python -m pytest security_tests/student_2_privacy/test_privacy_assessment.py -q -s
   ```

4. Record every actual result in `report_template.md` and attach evidence using `evidence/README.md`.

5. Repeat relevant cases manually in Streamlit using synthetic accounts `privacy_user_a` and `privacy_user_b`, plus `PRIVACY-CANARY-2026-ALPHA`.

6. Complete `findings/risk_register.csv`, justify impact and likelihood, then export the report to PDF.

## Safety rules

- Test only the local application and databases you own.
- Use a disposable copy of `data/` for manual testing.
- Never use real passwords, API keys, identity numbers, bank details, or portfolio values.
- Do not modify existing repository data during testing.

## Assessment hypothesis

Privacy controls may be applied at the UI/session layer but not consistently enforced at persistence and helper-function boundaries. The cheapest disconfirming check is saving synthetic user A and user B history, then loading it with no user context and with each user context.