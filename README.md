# Landfall

A safe, open-source Windows to Linux migration assistant.

Landfall runs on Windows, tells you which of your apps and devices will work on Linux,
packs your files and browser profiles into one encrypted bundle, and unpacks them on any
Linux distro. It only ever reads from your Windows drive.

**Status:** Phase 0 - build pipeline only. Not ready for use.

## Roadmap

- [ ] Phase 0 - Setup and build pipeline
- [ ] Phase 1 - Readiness report (v0.1)
- [ ] Phase 2 - Encrypted bundle (v0.2)
- [ ] Phase 3 - Linux importer (v0.3)
- [ ] Phase 4 - Public launch (v1.0)

## Run from source

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m landfall
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
