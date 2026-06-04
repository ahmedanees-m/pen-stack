# Releasing PEN-STACK to PyPI

Publishing is automated by `.github/workflows/publish.yml` using **PyPI Trusted Publishing** (OIDC) - no API
token is stored in the repo. A version tag (`v*`) builds the sdist + wheel, runs `twine check`, and publishes.

## One-time setup (PyPI side)

1. Log in to <https://pypi.org> and go to **Your projects -> Publishing -> Add a pending publisher**
   (this works before the first release, so the project name is claimed on first publish).
2. Fill in:
   - **PyPI project name:** `pen-stack`
   - **Owner:** `ahmedanees-m`  -  **Repository:** `pen-stack`
   - **Workflow name:** `publish.yml`
   - **Environment:** `pypi`
3. (Optional) repeat for TestPyPI with environment `testpypi`.
4. In the GitHub repo, create the environments `pypi` (and `testpypi`) under **Settings -> Environments**.

No secrets are needed: OIDC proves the workflow's identity to PyPI.

## Cut a release

```bash
# 1. bump the version in pyproject.toml, pen_stack/__init__.py, CITATION.cff
# 2. update CHANGELOG.md
# 3. commit, then tag and push the tag:
git tag -a v3.1.1 -m "PEN-STACK v3.1.1"
git push origin v3.1.1            # -> publish.yml builds + publishes to PyPI
```

`v3.1.0` was tagged before `publish.yml` existed, so it did not auto-publish. To publish `3.1.0` either run
the workflow manually (**Actions -> Publish to PyPI -> Run workflow**, target `pypi`) or upload the prebuilt
artifacts once (see below); subsequent tags publish automatically.

## Manual fallback (token)

If you prefer a token over trusted publishing:

```bash
python -m build                  # -> dist/pen_stack-<ver>.tar.gz + .whl
python -m twine check dist/*
python -m twine upload dist/*     # prompts for __token__ + a PyPI API token (pypi-...)
```

## Dry-run on TestPyPI

```bash
# Actions -> Publish to PyPI -> Run workflow -> target: testpypi
pip install -i https://test.pypi.org/simple/ pen-stack
```

## Checklist

- [ ] Version bumped consistently (pyproject / `__init__` / CITATION.cff); `test_ws_h` enforces this.
- [ ] CHANGELOG entry; README + badges updated.
- [ ] CI green; single contributor; pre-registration SHA-locked.
- [ ] `python -m twine check dist/*` passes.
- [ ] Tag pushed; PyPI badge resolves; GitHub release notes from the CHANGELOG.
- [ ] Zenodo data deposit (DOI) for any data release.
