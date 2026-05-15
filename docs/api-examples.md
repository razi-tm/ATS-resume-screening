# API Examples

```bash
curl http://localhost:8000/api/v1/health
```

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"organization_name":"Acme Talent","email":"admin@example.com","password":"correct-horse-battery"}'
```
