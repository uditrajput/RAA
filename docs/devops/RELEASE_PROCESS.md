# Controlled Production Release Process

## Release Philosophy
Releases of RAA are strictly controlled, immutable, signed, and traceable. No code is published directly to GitHub Releases or PyPI without passing the entire quality and security matrix.

---

## 1. Release Lifecycle & Prerequisites

Before initiating a release:
1. All changes must be merged into `main` via reviewed Pull Requests.
2. The `main` branch CI status must be completely green across all status checks.
3. Version numbers must be synchronized across:
   - `pyproject.toml` (`version = "X.Y.Z"`)
   - `src/raa/version.py` (`__version__ = "X.Y.Z"`)
   - `docs/DEPLOYMENT.md` and `RELEASES.md`

---

## 2. Release Steps

### Step 1: Create a Release Tag
Releases are triggered by pushing a signed Git tag following Semantic Versioning (`v*.*.*`):

```bash
git checkout main
git pull origin main
git tag -a v4.0.0 -m "Release v4.0.0: Autonomous Mobile Intelligence & Self-Evolving Ecosystem"
git push origin v4.0.0
```

### Step 2: Automated Pipeline Execution
Pushing the tag triggers `.github/workflows/release.yml`:
1. **Pre-release Check:** Runs complete test suite on the tagged commit.
2. **Build Distribution:** Builds `.tar.gz` (sdist) and `.whl` (wheel) via `build`.
3. **Artifact Integrity:** Verifies wheel metadata with `twine check`.
4. **Checksum Generation:** Produces `SHA256SUMS`.
5. **SBOM Generation:** Native invocation of `raa admin sbom` for both CycloneDX and SPDX.
6. **Publishing:** Packages and release notes are attached to the official GitHub Release.

---

## 3. Post-Release Verification
- Download the generated `.whl` package and verify in a clean sandbox:
  ```bash
  python -m venv test_env
  source test_env/bin/activate # or test_env\Scripts\activate on Windows
  pip install raa-4.0.0-py3-none-any.whl
  raa doctor
  raa --version
  ```
- Validate SHA256 matches `SHA256SUMS`.
