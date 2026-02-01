# CI Artifact Generation Scripts

This directory contains scripts for generating comprehensive CI/CD artifacts for the ShuangxiangApp project.

## Scripts

### `generate-artifacts.sh`

**Purpose:** Generates all required CI artifacts for the project, including dependency analysis, security checks, test reports, observability data, and runbooks.

**Usage:**
```bash
./scripts/generate-artifacts.sh
```

**What it generates:**

#### Audit Artifacts (3 files)
- `artifacts/audit/dependency-integrity-report.md` - Comprehensive 40-point checklist covering:
  - Package lock file validation
  - Dependency version control
  - Security vulnerability assessment
  - License compliance
  - Supply chain integrity
  - SBOM considerations
- `artifacts/audit/report-validation-result.json` - JSON validation result (PASS/FAIL)
- `artifacts/audit/report-validation-log.txt` - Detailed validation log

#### Dependency Artifacts (10 files)
**Flutter (3 files):**
- `artifacts/deps/flutter/pub-resolved.txt` (N/A - no Flutter project)
- `artifacts/deps/flutter/pub-sources.txt` (N/A - no Flutter project)
- `artifacts/deps/flutter/package-resolve-paths.txt` (N/A - no Flutter project)

**Node.js (3 files):**
- `artifacts/deps/node/node-resolved.txt` - Full dependency tree from npm ls
- `artifacts/deps/node/node-sources.txt` - Registry sources and direct dependencies
- `artifacts/deps/node/node-resolve-paths.txt` - Module resolution paths

**Python (1 file):**
- `artifacts/deps/python/python-deps-status.txt` (N/A - no Python dependencies yet)

#### Security Artifacts (2 files)
- `artifacts/security/shadowing-check.txt` - Checks for dependency shadowing and scope confusion
- `artifacts/security/duplicate-module-names.txt` - Identifies duplicate/conflicting versions

#### Static Analysis Artifacts (2 files)
- `artifacts/static/ununsed-imports.txt` - Detects potentially unused imports in TypeScript
- `artifacts/static/false-integration-check.txt` - Scans for mocks/stubs in production code

#### Test Artifacts (3 files)
- `artifacts/tests/flutter-test-report.txt` (N/A - no Flutter project)
- `artifacts/tests/nest-test-report.txt` - NestJS unit test results
- `artifacts/tests/e2e-ws-report.txt` - E2E WebSocket test documentation

#### Observability Artifacts (4 files)
- `artifacts/observability/trace-export.json` - OpenTelemetry trace export structure
- `artifacts/observability/correlation-ids.txt` - Correlation ID configuration details
- `artifacts/observability/service-logs.txt` - Logging framework configuration
- `artifacts/observability/e2e-timeline.txt` - E2E test execution timeline template

#### Runbook Artifacts (2 files)
- `artifacts/runbook/repro-steps.md` - Complete reproduction guide covering:
  - Prerequisites and system requirements
  - Initial setup instructions
  - Environment configuration
  - Test execution steps
  - Common issue reproduction
  - Debugging techniques
  - Troubleshooting checklist
- `artifacts/runbook/versions.txt` - Software version information

## Requirements

- **Bash:** 4.0 or higher
- **Node.js:** v18.x or v20.x
- **npm:** v9.x or higher
- **Git:** For version information

## Features

### Comprehensive Dependency Analysis
- Parses package.json and package-lock.json
- Extracts real dependency data (not just placeholders)
- Identifies scoped packages and their authenticity
- Checks for common security issues

### Technology Detection
- Automatically detects which technologies are present
- Marks N/A for missing technologies (Flutter, Python)
- Adapts artifact generation based on project structure

### 40-Point Integrity Checklist
The dependency integrity report includes 40 comprehensive checks:
1. Package lock files present
2. Lock file integrity match
3. No known vulnerable dependencies
4. Dependencies use specific versions
5. No wildcards in version specifications
6-40. [Full list in generated report]

Each check includes:
- **Status:** PASS/PARTIAL/REQUIRES_VERIFICATION/etc.
- **Evidence:** Concrete data from the project
- **Risk Level:** LOW/MEDIUM/HIGH
- **Conclusion:** Assessment and recommendations

### Validation
- Automatic validation of generated reports
- JSON output for CI/CD integration
- Detailed validation logs

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Generate CI Artifacts
  run: ./scripts/generate-artifacts.sh

- name: Upload Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: ci-artifacts
    path: artifacts/

- name: Validate Report
  run: |
    cat artifacts/audit/report-validation-result.json
    if [ "$(jq -r .validation_status artifacts/audit/report-validation-result.json)" != "PASS" ]; then
      echo "Validation failed"
      exit 1
    fi
```

### GitLab CI Example
```yaml
generate_artifacts:
  script:
    - ./scripts/generate-artifacts.sh
  artifacts:
    paths:
      - artifacts/
    reports:
      dotenv: artifacts/audit/report-validation-result.json
```

## Output Structure

```
artifacts/
├── audit/
│   ├── dependency-integrity-report.md  (comprehensive report)
│   ├── report-validation-result.json   (validation status)
│   └── report-validation-log.txt       (validation details)
├── deps/
│   ├── flutter/                        (N/A for this project)
│   ├── node/                           (active)
│   └── python/                         (N/A for now)
├── security/
│   ├── shadowing-check.txt
│   └── duplicate-module-names.txt
├── static/
│   ├── ununsed-imports.txt
│   └── false-integration-check.txt
├── tests/
│   ├── flutter-test-report.txt         (N/A)
│   ├── nest-test-report.txt
│   └── e2e-ws-report.txt
├── observability/
│   ├── trace-export.json
│   ├── correlation-ids.txt
│   ├── service-logs.txt
│   └── e2e-timeline.txt
└── runbook/
    ├── repro-steps.md
    └── versions.txt
```

## Troubleshooting

### Script fails with permission denied
```bash
chmod +x scripts/generate-artifacts.sh
```

### Missing Node.js dependencies
```bash
cd apps/backend
npm install
```

### Incomplete artifacts
The script validates all required files at the end. If any are missing, it will report them and exit with code 1.

## Maintenance

### Adding New Artifact Types
1. Create a new `generate_*_artifacts()` function
2. Add the function call to `main()`
3. Update `required_files` array for validation
4. Update this README

### Modifying Checklist Items
Edit the `generate_dependency_integrity_report()` function to add/modify checklist items. Ensure:
- Each item is numbered (1-40)
- Includes Status, Evidence, Risk Level, and Conclusion
- Update validation metrics accordingly

## Version History

- **v1.0.0** (2024-02-01): Initial release
  - 40-point dependency integrity checklist
  - Multi-technology support (Node.js, Flutter, Python)
  - Comprehensive security and static analysis
  - Observability and runbook artifacts

## License

This script is part of the ShuangxiangApp project and follows the project's license terms.
