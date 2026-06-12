# import-linter Configuration Patterns (verified 2026-06-11)

## Basic .importlinter File Structure

```ini
[importlinter]
root_package = your_package_name
include_external_packages = False

[importlinter:contract:contract_name]
name = Human readable description
type = layers|forbidden|independence
# type-specific fields below
```

## Contract Type: Layers

Enforces a strict top-down dependency order. Higher layers can import lower layers, but not vice versa.

```ini
[importlinter:contract:layers]
name = Layer dependency rules
type = layers
layers =
    myapp.api
    myapp.service
    myapp.infra
    myapp.domain
```

**Order matters**: First layer is highest (most external), last is lowest (most internal).

## Contract Type: Forbidden

Blocks specific import paths regardless of layer ordering.

```ini
[importlinter:contract:infra_no_domain]
name = Forbidden: infra -> domain (direct import)
type = forbidden
source_modules =
    myapp.infra
forbidden_modules =
    myapp.domain
```

Use this when you want to enforce that one module never imports another, even if the layer contract would technically allow it.

## Contract Type: Independence

Ensures two modules never import each other (bidirectional block).

```ini
[importlinter:contract:oil_water]
name = oil and water are independent
type = independence
modules =
    myapp.oil
    myapp.water
```

## Critical Configuration Gotchas

### root_package Must Match Directory Structure

If your project has top-level directories (domain/, service/, infra/), then:
- `root_package = domain` (or any single top-level package)
- NOT `root_package = myapp` if there is no myapp/ directory

The root_package tells import-linter where to start scanning imports. If it does not match an actual importable package, all contracts will pass vacuously (false negative).

### include_external_packages

Set to `True` when:
- Your `forbidden_modules` includes third-party packages
- You want to block imports of specific external libraries

Set to `False` when:
- You only care about internal module relationships
- You want faster analysis (skips external dependency graph)

### Multiple Contracts

You can have multiple contracts in one file. They are all checked independently:

```ini
[importlinter]
root_package = myapp
include_external_packages = False

[importlinter:contract:layers]
name = Layer ordering
type = layers
layers =
    myapp.api
    myapp.service
    myapp.domain

[importlinter:contract:repo_isolation]
name = Repositories are independent
type = independence
modules =
    myapp.infra.user_repo
    myapp.infra.order_repo
```

## Integration with unified-lint

The unified-lint tool generates `.importlinter` from `.unified-lint/arch.toml`:

```toml
# .unified-lint/arch.toml
root_package = "myapp"

[layers]
order = ["api", "infra", "service", "domain"]

[[contracts.forbidden]]
name = "infra cannot directly import domain"
from_layer = "infra"
to_layer = "domain"
```

The ImportLinterEngine converts this to the native `.importlinter` format automatically.
