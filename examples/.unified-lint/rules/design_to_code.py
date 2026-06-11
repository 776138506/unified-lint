"""Example custom rule: check design modules are implemented in code.

Usage in spec-chain.toml:

[[chains]]
source = "specs/design.md"
target = "src/"
rule = "design_to_code"
"""

from unified_lint.engines.spec_chain import chain_rule, Violation, Severity
from typing import Optional


@chain_rule("design_to_code")
def check_design_to_code(
    source: dict, target: dict, source_file: str, target_file: str,
    params: Optional[dict] = None
) -> list[Violation]:
    """Check that design modules are implemented in code."""
    violations = []
    
    # Extract design modules from source
    design_modules = {m["name"] for m in source.get("modules", [])}
    
    # Extract implemented modules from target
    implemented = set(target.get("implemented_modules", []))
    
    # Check coverage
    for module in design_modules - implemented:
        violations.append(Violation(
            rule_id="design_to_code",
            message="Design module '{}' not implemented in code".format(module),
            file=target_file,
            severity=Severity.ERROR,
            engine="spec-chain",
        ))
    
    return violations
