---
specmd:
  schema: 1
  id: SMD-EX-DOC-001
  kind: behavioral
---

# Example: charging canceled orders

This is a fictitious example of the format proposed for SpecMD. It is not a product rule accepted by the user, it has no acceptance receipt and it does not indicate that step implementations or run tests exist in this repository.

The Markdown is the canonical source of this example. The scenarios below must be interpretable from this file, without requiring a parallel `.feature` file or a mandatory step of writing that file.

## SMD-EX-REQ-001 — Do not generate charges for canceled orders

A canceled order must not generate a new charge when its charge event is processed. The rule also applies to repeated attempts to process the same event.

This example checks canceled orders that do not have charges yet. It does not decide refund policies, cancellation of paid orders or authorization to cancel: those decisions would need requirements of their own, if they were necessary for the real product.

```gherkin
@SMD-EX-REQ-001
Feature: Prevent new charges for canceled orders

  @SMD-EX-SCN-001
  Scenario: Process a charge event after cancellation
    Given a canceled order that has no charges
    When the charge event of that order is processed
    Then no charge should be created for that order

  @SMD-EX-SCN-002
  Scenario: Repeat the processing of the charge event
    Given a canceled order that has no charges
    When the same charge event of that order is processed twice
    Then no charge should be created for that order
```

## Expected review and evidence

Before implementing this behavior in a real product, the user would need to review the rule, the explicit limits and the two scenarios. The acceptance would be recorded through a protected channel and bound to the hash, path and scope of this version.

After acceptance, the runner would need to find step implementations and produce evidence bound to the contract and to the code actually run. Undefined steps, skipped scenarios or old results would not meet the completion criterion.

An implementation that simply makes no assertions could still produce an appearance of success. The strength of the check requires additional assessment; the valid syntax of the scenarios does not establish that guarantee.

If an agent introduces another limit, such as a maximum period for cancellation, that change will need to appear as a behavior proposal. Writing a test for that limit does not turn it into an accepted requirement.

See the [proposed format](../docs/format.md), the acceptance mechanism (removed by [D-021](../docs/decisions.md)) and the [validation plan](../docs/validation-plan.md).
