# Quick Start Guide - CI Artifacts

## Generate All Artifacts

```bash
./scripts/generate-artifacts.sh
```

## Verify Artifacts

```bash
# List all generated artifacts
ls -R artifacts/

# Check validation status
cat artifacts/audit/report-validation-result.json | grep validation_status

# View comprehensive report
less artifacts/audit/dependency-integrity-report.md
```

## Key Artifacts to Review

### 1. Dependency Integrity Report
**File:** `artifacts/audit/dependency-integrity-report.md`  
**Contents:** 40-point comprehensive checklist of dependency security and integrity

**Quick View:**
```bash
cat artifacts/audit/dependency-integrity-report.md | less
```

### 2. Validation Result
**File:** `artifacts/audit/report-validation-result.json`  
**Contents:** JSON validation status (PASS/FAIL)

**Quick Check:**
```bash
jq . artifacts/audit/report-validation-result.json
```

### 3. Node.js Dependencies
**Files:**
- `artifacts/deps/node/node-resolved.txt` - Full dependency tree
- `artifacts/deps/node/node-sources.txt` - Registry sources
- `artifacts/deps/node/node-resolve-paths.txt` - Resolution paths

**Quick View:**
```bash
head -50 artifacts/deps/node/node-sources.txt
```

### 4. Security Checks
**Files:**
- `artifacts/security/shadowing-check.txt` - Dependency shadowing analysis
- `artifacts/security/duplicate-module-names.txt` - Duplicate detection

**Quick View:**
```bash
cat artifacts/security/shadowing-check.txt
```

### 5. Reproduction Guide
**File:** `artifacts/runbook/repro-steps.md`  
**Contents:** Complete setup and troubleshooting guide

**Quick View:**
```bash
less artifacts/runbook/repro-steps.md
```

## CI/CD Usage

### Validate in CI Pipeline
```bash
# Generate artifacts
./scripts/generate-artifacts.sh

# Check validation status
if [ "$(jq -r .validation_status artifacts/audit/report-validation-result.json)" != "PASS" ]; then
  echo "Validation failed!"
  exit 1
fi

echo "All artifacts generated successfully!"
```

### Upload to Artifact Storage
```bash
# GitHub Actions
- uses: actions/upload-artifact@v3
  with:
    name: ci-artifacts
    path: artifacts/

# GitLab CI
artifacts:
  paths:
    - artifacts/
```

## Understanding the 40-Point Checklist

The dependency integrity report includes 40 checks covering:

**Security (items 1-20):**
- Lock files and integrity
- Vulnerability scanning
- Package source verification
- Typosquatting detection
- License compliance

**Operational (items 21-30):**
- Peer dependencies
- Circular dependencies
- Type definitions
- Build reproducibility
- Complexity analysis

**Governance (items 31-40):**
- Update policies
- SBOM generation
- Provenance verification
- Compliance checks

Each item includes:
- ✓ **Status** (PASS/PARTIAL/REQUIRES_VERIFICATION/etc.)
- 📋 **Evidence** (concrete project data)
- ⚠️ **Risk Level** (LOW/MEDIUM/HIGH)
- 💡 **Conclusion** (recommendations)

## Artifact Summary

| Category | Files | Status |
|----------|-------|--------|
| Audit | 3 | ✓ Generated |
| Flutter Deps | 3 | ✓ N/A (no Flutter) |
| Node.js Deps | 3 | ✓ Generated |
| Python Deps | 1 | ✓ N/A (no Python) |
| Security | 2 | ✓ Generated |
| Static Analysis | 2 | ✓ Generated |
| Tests | 3 | ✓ Generated |
| Observability | 4 | ✓ Generated |
| Runbook | 2 | ✓ Generated |
| **Total** | **23** | **✓ Complete** |

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/generate-artifacts.sh
```

### Missing Dependencies
```bash
cd apps/backend
npm install
```

### Artifacts Not Generated
Check the script output for errors:
```bash
./scripts/generate-artifacts.sh 2>&1 | tee artifact-generation.log
```

## For More Details

See `scripts/README.md` for comprehensive documentation.
