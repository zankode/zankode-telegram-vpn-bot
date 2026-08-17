import unittest

from telegram import InlineKeyboardButton
from telegram.ext import Application


class PTBContractTest(unittest.TestCase):
    def test_required_ptb_22_8_runtime_api_is_available(self):
        builder = Application.builder()
        self.assertTrue(callable(getattr(builder, "post_init", None)))
        self.assertTrue(callable(getattr(builder, "post_stop", None)))
        self.assertTrue(callable(getattr(builder, "post_shutdown", None)))
        self.assertTrue(callable(getattr(Application, "create_task", None)))

        # Zankode uses the Bot API button appearance fields exposed by the pinned PTB.
        button = InlineKeyboardButton(
            "Test",
            callback_data="test",
            style="primary",
            icon_custom_emoji_id="5312016608254762256",
        )
        self.assertEqual(button.callback_data, "test")
