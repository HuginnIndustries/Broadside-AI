# Release Process

Use this checklist when publishing Broadside-AI.

## One-time repository setup

1. Enable PyPI Trusted Publishing for `HuginnIndustries/Broadside-AI`.
2. If `broadside-ai` does not exist on PyPI yet, create a pending publisher so the first trusted publish can create the project.
3. Optionally enable TestPyPI Trusted Publishing for the manual `publish-testpypi.yml` workflow.
4. Add `pypi` and `testpypi` environments in GitHub with the protections you want.
5. Confirm the publish workflows can request `id-token: write`.

### Trusted publisher values

**PyPI** (create as pending publisher at <https://pypi.org/manage/account/publishing/>):

| Field             | Value                                  |
| ----------------- | -------------------------------------- |
| Project name      | `broadside-ai`                         |
| Owner             | `HuginnIndustries`                     |
| Repository name   | `Broadside-AI`                         |
| Workflow name     | `publish.yml`                          |
| Environment name  | `pypi`                                 |

**TestPyPI** (create at <https://test.pypi.org/manage/account/publishing/>):

| Field             | Value                                  |
| ----------------- | -------------------------------------- |
| Project name      | `broadside-ai`                         |
| Owner             | `HuginnIndustries`                     |
| Repository name   | `Broadside-AI`                         |
| Workflow name     | `publish-testpypi.yml`                 |
| Environment name  | `testpypi`                             |

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
- successful clean-venv wheel smoke test
- successful CLI smoke checks

## Pre-publish review

Before cutting a release, verify:

- `README.md` matches actual runtime behavior
- install instructions are accurate
- benchmark claims are backed by committed snapshots
- package metadata in `pyproject.toml` is current
- there are no local cache or output artifacts in the repo tree
- the CLI JSON contract still matches the documented schema version

## Recommended first-release path

For the first public release, do a TestPyPI dry run before publishing to PyPI:

1. Configure a pending publisher on PyPI for `broadside-ai`.
2. Configure a trusted publisher on TestPyPI for `.github/workflows/publish-testpypi.yml`.
3. Run the manual `Publish TestPyPI` workflow from GitHub Actions.
4. Install from TestPyPI in a clean environment and verify the CLI.
5. Cut the real GitHub release and let `publish.yml` upload to PyPI.

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
- `pipx install broadside-ai` works in a clean environment
- the `broadside-ai` console script works
- `python -m broadside_ai` works

If a release fails after upload starts, do not overwrite artifacts. Cut a new
version instead.
