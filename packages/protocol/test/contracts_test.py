from __future__ import annotations

import unittest

from enshittify_protocol import (
    AgentAction,
    AgentRunSummary,
    ModelUsage,
    ProviderDescriptor,
)


class ProtocolContractTests(unittest.TestCase):
    def test_agent_summary_serializes_stable_provider_and_action_contracts(
        self,
    ) -> None:
        action = AgentAction(
            sequence=1,
            actor="model",
            kind="rewrite",
            path="main.py",
            tool="llm_rewrite",
            status="planned",
            summary="Planned a rewrite.",
        )
        summary = AgentRunSummary(
            mode="agent",
            provider=ProviderDescriptor(
                name="fake",
                model="scripted",
                capabilities=("tool_calling",),
            ),
            actions=(action,),
        )

        payload = summary.model_dump(mode="json")

        self.assertEqual(payload["provider"]["name"], "fake")
        self.assertEqual(payload["actions"][0]["path"], "main.py")
        self.assertNotIn("api_key", str(payload))

    def test_model_usage_aggregates_missing_total_from_input_and_output(self) -> None:
        usage = ModelUsage(input_tokens=10).plus(ModelUsage(output_tokens=4))
        self.assertEqual(usage.total_tokens, 14)


if __name__ == "__main__":
    unittest.main()
