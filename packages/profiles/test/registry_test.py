from __future__ import annotations

import unittest

from enshittify_profiles import get_profile, list_profiles
from enshittify_tools.catalog import list_mutation_tool_names


class ProfileRegistryTests(unittest.TestCase):
    def test_profiles_reference_registered_tools(self) -> None:
        registered = set(list_mutation_tool_names())
        self.assertGreaterEqual(len(list_profiles()), 6)
        for profile in list_profiles():
            self.assertTrue(set(profile.tools) <= registered)

    def test_maximum_and_aliases(self) -> None:
        maximum = get_profile("maximum")
        self.assertEqual(maximum.select_tools("maximum"), list(maximum.tools))
        self.assertEqual(get_profile("max").name, "maximum")
        self.assertEqual(get_profile("enterprise").name, "enterprise-sprawl")


if __name__ == "__main__":
    unittest.main()
