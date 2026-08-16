from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from enshittify_providers import (
    CodxProvider,
    ProviderConfigurationError,
    create_provider,
    list_provider_specs,
    wrap_chat_model,
)
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_exposes_deterministic_codx_and_groq_modes(self) -> None:
        self.assertEqual(
            [spec.name for spec in list_provider_specs()], ["none", "codx", "groq"]
        )
        self.assertIsNone(create_provider("none"))

    def test_codx_provider_uses_wrapper_without_an_api_key(self) -> None:
        with patch(
            "enshittify_providers.adapters.codx.shutil.which",
            return_value="/usr/local/bin/codx",
        ):
            provider = create_provider("codx", codx_command="codx")

        self.assertIsInstance(provider, CodxProvider)
        assert isinstance(provider, CodxProvider)
        self.assertEqual(provider.command, "codx")
        self.assertTrue(provider.yolo)
        self.assertIsNone(provider.chat_model)

    def test_groq_requires_a_key_without_leaking_one(self) -> None:
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": ""}),
            self.assertRaisesRegex(ProviderConfigurationError, "GROQ_API_KEY"),
        ):
            create_provider("groq")

        raw_key = "gsk_test_key_that_must_not_leak"
        provider = create_provider("groq", api_key=raw_key)
        self.assertIsNotNone(provider)
        assert provider is not None
        self.assertEqual(provider.name, "groq")
        self.assertNotIn(raw_key, repr(provider.chat_model))
        self.assertNotIn(raw_key, str(provider.descriptor().model_dump()))

    def test_any_langchain_chat_model_can_be_wrapped(self) -> None:
        model = FakeMessagesListChatModel(responses=[AIMessage(content="done")])
        provider = wrap_chat_model(model, name="fixture", model="scripted")
        self.assertEqual(provider.descriptor().name, "fixture")
        self.assertIs(provider.chat_model, model)


if __name__ == "__main__":
    unittest.main()
