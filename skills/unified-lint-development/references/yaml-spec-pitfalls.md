# YAML Spec Design Pitfalls (2026-06-12)

## Pitfall 1: Context as Sibling of Semantic

**WRONG**:
```yaml
features:
  - id: "FEAT-001"
    name: "..."

context:           # ✗ Sibling level - which feature does this belong to?
  rationale: "..."
```

**CORRECT**:
```yaml
features:
  - id: "FEAT-001"
    name: "..."
    context:       # ✓ Field within the feature
      rationale: "..."
```

**Lesson**: All information about an object MUST be fields within that object, not sibling sections.

## Pitfall 2: Features at Same Level as PRD

**WRONG**:
```
specs/
├── prd/
├── features/      # ✗ Same level as prd
├── api/           # ✗ Same level as prd
└── biz-arch/      # ✗ Same level as prd
```

**CORRECT**:
```
specs/
├── prd.yaml       # Root
├── prd/
│   ├── REQ-001.yaml
│   └── features/  # ✓ Derived from prd
└── biz-arch.yaml  # Derived from prd
    └── biz-arch/
```

**Lesson**: PRD is the root. Everything else derives from it. Directory structure reflects derivation hierarchy.

## Pitfall 3: Development Log as Separate File

**WRONG**:
```
features/FEAT-001/
├── feature.yaml
├── dev_log.yaml    # ✗ Separate file
└── constraints.yaml # ✗ Separate file
```

**CORRECT**:
```yaml
# features/FEAT-001.yaml
dev_log:            # ✓ Field within feature
  stages: [...]
constraints:        # ✓ Field within feature
  technical: [...]
```

**Lesson**: Development logs, constraints, prompts, context are ALL fields within the object, not separate files.

## Pitfall 4: Module Without Directory

**WRONG**:
```
biz-arch/
├── AuthService.yaml    # ✗ No directory for further decomposition
└── OrderService.yaml
```

**CORRECT**:
```
biz-arch/
└── modules/
    ├── AuthService/    # ✓ Directory allows further decomposition
    │   ├── module.yaml
    │   └── interfaces/
    └── OrderService/
        └── module.yaml
```

**Lesson**: Modules that might need further decomposition should be directories, not single files.

## Pitfall 5: Confusing Directory Structure with Logical Structure

**Wrong thinking**: "Directory structure = logical structure"

**Correct thinking**: 
- Directory structure = human-readable hierarchy (tree)
- File internal fields = logical relationships (network topology)
- ID references = cross-file dependencies (graph)

**Lesson**: Directories are for humans. Fields and references are for machines.
