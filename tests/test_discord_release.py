"""Release delivery contracts; requests are simulated and never reach Discord."""
import json
from pathlib import Path
import sys
import ssl
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import announce_release as delivery

PRIMARY = "https://discord.com/api/webhooks/100/changelog-test-token"
TARGET = "https://discord.com/api/webhooks/200/romarrng-test-token"


class FakeDiscord:
    def __init__(self, fail_target=False, corrupt=False):
        self.calls = []
        self.fail_target = fail_target
        self.corrupt = corrupt

    def __call__(self, url, payload=None):
        self.calls.append((url, payload))
        target = "/200/" in url
        if payload is None:
            return {"guild_id": "1", "channel_id": "20" if target else "10"}
        if target and self.fail_target:
            raise delivery.DeliveryError("Target unavailable")
        message = {"id": str(1000 + len(self.calls)),
                   "channel_id": "20" if target else "10"}
        if "embeds" in payload:
            description = "changed" if self.corrupt else payload["embeds"][0]["description"]
            message["embeds"] = [{"description": "  " + description + "\n"}]
        else:
            message["content"] = payload["content"]
        return message


class DiscordReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="romarrng-discord-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "receipts.json"
        self.arguments = dict(
            notes="First paragraph.\n" * 250, tag="v1.2.3", image="example:1.2.3",
            release_url="https://github.com/example/project/releases/tag/v1.2.3",
            workflow_url="https://github.com/example/project/actions/runs/1",
            changelog_webhook=PRIMARY, romarrng_webhook=TARGET,
            receipt_file=self.path, sleep=lambda _seconds: None)

    def test_links_first_announcement_only_after_all_chunks_are_accepted(self):
        fake = FakeDiscord()
        receipts = delivery.announce(**self.arguments, request=fake)
        posts = [(url, body) for url, body in fake.calls if body is not None]
        self.assertGreater(len(receipts["changelog_messages"]), 1)
        self.assertTrue(all("/100/" in url for url, _ in posts[:-1]))
        self.assertIn("/200/", posts[-1][0])
        self.assertIn(receipts["changelog_messages"][0]["url"], posts[-1][1]["content"])
        self.assertNotIn("First paragraph", posts[-1][1]["content"])
        for url, body in posts:
            self.assertIn("wait=true", url)
            self.assertEqual(body["allowed_mentions"], {"parse": []})
        self.assertTrue(all(row["verified"] for row in receipts["changelog_messages"]))
        self.assertNotIn("test-token", self.path.read_text())

    def test_resume_link_failure_without_reposting_changelog(self):
        fake = FakeDiscord(fail_target=True)
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**self.arguments, request=fake)
        saved = json.loads(self.path.read_text())
        self.assertTrue(saved["changelog_messages"])
        retry = FakeDiscord()
        result = delivery.announce(**self.arguments, request=retry)
        posts = [url for url, payload in retry.calls if payload is not None]
        self.assertEqual(len(posts), 1)
        self.assertIn("/200/", posts[0])
        self.assertTrue(result["romarrng_message"]["verified"])
        again = FakeDiscord()
        delivery.announce(**self.arguments, request=again)
        self.assertFalse(any(payload is not None for _, payload in again.calls))

    def test_retains_accepted_id_on_changed_text_and_does_not_crosspost(self):
        fake = FakeDiscord(corrupt=True)
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**self.arguments, request=fake)
        saved = json.loads(self.path.read_text())
        self.assertTrue(saved["changelog_messages"][0]["id"])
        self.assertNotIn("romarrng_message", saved)
        retry = FakeDiscord()
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**self.arguments, request=retry)
        self.assertFalse(any(payload is not None for _, payload in retry.calls))

    def test_changed_release_body_cannot_reuse_receipts(self):
        delivery.announce(**self.arguments, request=FakeDiscord())
        changed = {**self.arguments, "notes": "Different notes."}
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**changed, request=FakeDiscord())

    def test_empty_notes_make_no_requests(self):
        fake = FakeDiscord()
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**{**self.arguments, "notes": " \n"}, request=fake)
        self.assertEqual(fake.calls, [])

    def test_same_channel_rejected_before_posting(self):
        def request(url, payload=None):
            self.assertIsNone(payload)
            return {"guild_id": "1", "channel_id": "10"}
        with self.assertRaises(delivery.DeliveryError):
            delivery.announce(**self.arguments, request=request)

    def test_rejects_non_discord_or_plaintext_webhooks(self):
        for url in ("http://discord.com/api/webhooks/1/token",
                    "https://example.com/api/webhooks/1/token",
                    "https://discord.com.evil.example/api/webhooks/1/token"):
            with self.subTest(url=url), self.assertRaises(delivery.DeliveryError):
                delivery.webhook_url(url)

    def test_network_errors_never_print_webhook_credentials(self):
        with patch.object(delivery, "HTTPSConnection") as connection:
            connection.return_value.request.side_effect = OSError(PRIMARY)
            with self.assertRaises(delivery.DeliveryError) as caught:
                delivery.request_json(PRIMARY, {"content": "hello"})
            self.assertNotIn("test-token", str(caught.exception))
            self.assertEqual(connection.call_args.args, ("discord.com",))
            self.assertEqual(connection.call_args.kwargs["timeout"], 30)
            context = connection.call_args.kwargs["context"]
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
            connection.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
