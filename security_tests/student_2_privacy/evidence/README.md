# Evidence Collection Guide

Create one file or screenshot per test ID using synthetic values only.

## Recommended naming

```text
T01-password-storage.png
T04-unauthenticated-history.json
T05-cross-user-isolation.png
T09-audit-redaction.log
```

## What to capture

- UI tests: browser screenshot showing account context, action, result, and timestamp.
- File tests: short sanitized excerpt, file path, and hash if useful.
- MongoDB tests: collection name, query shape, returned field names, and synthetic values; do not export a whole database.
- CLI tests: command, exit code, and relevant output. Redact tokens before storing output.

For each evidence item add a short note stating what it proves and what it does not prove. Keep raw captures outside version control if they contain anything sensitive.