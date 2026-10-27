---
specmd:
  schema: 1
  id: SMD-EX-DOC-002
  kind: reference
  exemption_reason: "Guidance about the contributor's editor; does not establish behaviors of the product being developed."
---

# Example: editor setup

This document illustrates a proposed classification as reference. The justification in the frontmatter was written by the agent and needs human acceptance bound to this version. There is no approved exemption nor acceptance receipt in this example.

## Local suggestions

To make reading the documentation easier, the contributor can:

- Enable line numbers.
- Use the editor's Markdown preview.
- Show whitespace and line breaks while reviewing a diff.
- Keep a tab with the complete document open while checking their changes.

These suggestions are editing preferences. They do not define inputs, responses, permissions or external effects of the software that will be developed.

## Why there is no Gherkin

No artificial scenarios were included to check editor preferences. The exemption depends on the user agreeing that the reviewed content does not establish behavioral obligations of the product.

Once accepted, this classification allows reusing the analysis while the content and the applicable context remain valid. The file stays in the inventory and its changes are still detected.

If someone adds a business rule here, the hash will change and the classification must be reassessed. The agent may propose turning the document into a mixed one or moving the rule to an appropriate contract; it may not keep an old exemption for the new content.

See the [proposed format](../docs/format.md), the [incremental index](../docs/indexing.md) and the acceptance mechanism (removed by [D-021](../docs/decisions.md)).
