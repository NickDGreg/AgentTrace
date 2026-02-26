# FRONTEND

AgentTrace frontend surfaces are synthetic site UIs under `sites/`.

Primary expectations:
- pages are deterministic and reproducible
- UI complexity exists only to model agent failure modes
- no unnecessary visual fidelity work

UI testing and screenshots:
- run stack: `docker compose -f sites/<site>/compose.yaml up -d`
- capture screenshot: `python tools/ui_snapshot.py --url <start_url> --out results/ui/<name>.png --full-page`
- optional interaction: repeat `--click <selector>` and use `--wait-for-selector <selector>`

UI contracts should be verified with tests in `tests/test_*_site.py`.
