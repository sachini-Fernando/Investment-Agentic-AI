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
```

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