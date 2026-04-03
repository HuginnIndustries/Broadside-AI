# Release Process

Use this checklist when publishing Broadside-AI.

## One-time repository setup

1. Enable PyPI Trusted Publishing for `HuginnIndustries/Broadside-AI`.
2. Add a `pypi` environment in GitHub with the protections you want.
3. Confirm the publish workflow can request `id-token: write`.

## Local release gate

Install release tooling:

```bash
pip install -e ".[dev]"
```

Run the full release check:

```bash
make clean
make release-check
python -m broadside_ai --help
python -m broadside_ai validate-task tasks/_template.yaml
```

That should produce:

- passing tests
- passing lint and format checks
- passing mypy
- fresh `dist/` artifacts
- successful `twine check`
- successful CLI smoke checks

## Pre-publish review

Before cutting a release, verify:

- `README.md` matches actual runtime behavior
- install instructions are accurate
- benchmark claims are backed by committed snapshots
- package metadata in `pyproject.toml` is current
- there are no local cache or output artifacts in the repo tree

## Publish flow

1. Update the version in `pyproject.toml` and `src/broadside_ai/__init__.py`.
2. Re-run `make release-check` and the CLI smoke checks above.
3. Commit the version bump and release-note updates.
4. Create and push a Git tag such as `v0.1.0`.
5. Create a GitHub Release for that tag.
6. Let the GitHub publish workflow upload the package to PyPI.

## Post-publish checks

Verify on GitHub and PyPI:

- release notes render correctly
- README renders correctly on PyPI
- `pip install broadside-ai` works in a clean environment
- the `broadside-ai` console script works
- `python -m broadside_ai` works

If a release fails after upload starts, do not overwrite artifacts. Cut a new
version instead.
