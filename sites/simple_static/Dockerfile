FROM python:3.12-slim

WORKDIR /site
COPY index.html /site/index.html
EXPOSE 8000

CMD ["sh", "-c", "echo \"[agenttrace] external URL: ${AGENTTRACE_EXTERNAL_URL:-http://localhost:18080/}\"; python -m http.server 8000 --bind 0.0.0.0"]
