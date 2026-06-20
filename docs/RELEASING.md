# Releasing PEN-STACK to PyPI

Publishing is automated by `.github/workflows/publish.yml`. A version tag (`v*`) builds the sdist + wheel,
runs `twine check`, and publishes. `skip-existing: true` means a version already on PyPI is skipped (not a
failure), so re-runs and already-published versions never fail the workflow.

## Authentication (configured: API token)

The workflow authenticates with an API token stored as the encrypted repo secret **`PYPI_API_TOKEN`**
(Settings -> Secrets and variables -> Actions). This is already set. To rotate it: create a new token at
<https://pypi.org/manage/account/token/> (project-scoped to `pen-stack` once the project exists) and update
the secret. For TestPyPI, add `TEST_PYPI_API_TOKEN`.

### Alternative: tokenless Trusted Publishing (OIDC)

To avoid storing a token, switch to Trusted Publishing: on PyPI add a publisher under
**Your projects -> pen-stack -> Publishing** (owner `ahmedanees-m`, repo `pen-stack`, workflow `publish.yml`,
environment `pypi`), create the GitHub `pypi` environment, and in `publish.yml` replace the
`password: ${{ secrets.PYPI_API_TOKEN }}` line with `permissions: { id-token: write }` on the job. No secret
is then needed.

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
