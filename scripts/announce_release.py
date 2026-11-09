#!/usr/bin/env python3
"""Post full release notes to #changelogs, then a jump link to #romarrng."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
from http.client import HTTPException, HTTPSConnection
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from release_notes import split_discord_body


class DeliveryError(RuntimeError):
    pass


def webhook_url(value: str, *, wait: bool = False) -> str:
    url = urlsplit(value)
    if (url.scheme != "https" or url.netloc != "discord.com"
            or not re.fullmatch(r"/api/(?:v\d+/)?webhooks/\d+/[A-Za-z0-9_-]+", url.path)
            or url.fragment):
        raise DeliveryError("Expected an HTTPS Discord webhook URL.")
    query = dict(parse_qsl(url.query))
    query.pop("wait", None)
    if wait:
        query["wait"] = "true"
    return urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ""))


def request_json(url: str, payload: dict | None = None) -> dict:
    webhook_url(url)  # Restrict the destination before using its path/query.
    parsed = urlsplit(url)
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    # Python 3.12+: fixed host, verified certificates/hostname, TLS 1.2+; no redirects.
    connection = HTTPSConnection("discord.com", timeout=30, context=context)  # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected
    try:
        connection.request(
            "POST" if payload is not None else "GET",
            parsed.path + ("?" + parsed.query if parsed.query else ""),
            body=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json", "User-Agent": "ROMarrNG-Releases/1.0"})
        response = connection.getresponse()
        if response.status >= 300:
            raise DeliveryError(f"Discord returned HTTP {response.status}.")
        result = json.load(response)
    except (HTTPException, OSError):
        raise DeliveryError("Discord response unavailable; inspect receipts before retrying.") from None
    except ValueError:
        raise DeliveryError("Discord returned invalid JSON; inspect delivery before retrying.") from None
    finally:
        connection.close()
    if not isinstance(result, dict):
        raise DeliveryError("Discord returned an unexpected response.")
    return result


def jump_url(guild: str, channel: str, message: str) -> str:
    if not all(str(value).isdigit() for value in (guild, channel, message)):
        raise DeliveryError("Discord response is missing a server, channel, or message ID.")
    return f"https://discord.com/channels/{guild}/{channel}/{message}"


def announce(*, notes: str, tag: str, image: str, release_url: str,
             workflow_url: str, changelog_webhook: str, romarrng_webhook: str,
             receipt_file: Path, request=request_json, sleep=time.sleep) -> dict:
    chunks = [chunk.strip() for chunk in split_discord_body(notes) if chunk.strip()]
    if not chunks:
        raise DeliveryError("Release notes are empty.")
    primary = webhook_url(changelog_webhook)
    target = webhook_url(romarrng_webhook)
    digest = hashlib.sha256(notes.encode()).hexdigest()
    receipts = (json.loads(receipt_file.read_text()) if receipt_file.exists()
                else {"tag": tag, "notes_sha256": digest, "changelog_messages": []})
    if receipts.get("tag") != tag or receipts.get("notes_sha256") != digest:
        raise DeliveryError("Receipts belong to different release notes; refusing duplicate delivery.")

    def save():
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = receipt_file.with_suffix(receipt_file.suffix + ".tmp")
        temporary.write_text(json.dumps(receipts, indent=2) + "\n")
        temporary.replace(receipt_file)

    primary_meta, target_meta = request(primary), request(target)
    if primary_meta.get("channel_id") == target_meta.get("channel_id"):
        raise DeliveryError("Changelog and link webhooks must target different channels.")
    # Validate the routing metadata before posting either message.
    jump_url(primary_meta.get("guild_id"), primary_meta.get("channel_id"), "0")
    jump_url(target_meta.get("guild_id"), target_meta.get("channel_id"), "0")
    sent = receipts["changelog_messages"]
    for index, chunk in enumerate(chunks):
        if index < len(sent):
            if not sent[index].get("verified"):
                raise DeliveryError("An accepted changelog message needs review; it was not reposted.")
            continue
        payload = {
            "username": "ROMarrNG Releases", "allowed_mentions": {"parse": []},
            "embeds": [{
                "title": f"ROMarrNG {tag} release notes ({index + 1}/{len(chunks)})",
                "url": release_url, "description": chunk, "color": 5814783,
                "fields": ([{"name": "Image", "value": image, "inline": False},
                            {"name": "Workflow", "value": workflow_url, "inline": False}]
                           if index == 0 else []),
            }],
        }
        message = request(webhook_url(primary, wait=True), payload)
        record = {"id": message.get("id"), "channel_id": message.get("channel_id"),
                  "verified": False}
        sent.append(record)
        save()  # Keep accepted IDs even if Discord normalizes the response.
        record["url"] = jump_url(primary_meta["guild_id"], record["channel_id"], record["id"])
        embeds = message.get("embeds") or [{}]
        record["verified"] = (record["channel_id"] == primary_meta["channel_id"]
                              and str(embeds[0].get("description", "")).strip() == chunk)
        save()
        if not record["verified"]:
            raise DeliveryError("Discord accepted a changelog message with changed text; inspect receipts.")
        if index + 1 < len(chunks):
            sleep(1)

    content = f"ROMarrNG {tag} is out! Read the changelog announcement: {sent[0]['url']}"
    if "romarrng_message" not in receipts:
        message = request(webhook_url(target, wait=True), {
            "username": "ROMarrNG Releases", "content": content,
            "allowed_mentions": {"parse": []},
        })
        record = {"id": message.get("id"), "channel_id": message.get("channel_id"),
                  "verified": False}
        receipts["romarrng_message"] = record
        save()
        record["url"] = jump_url(target_meta["guild_id"], record["channel_id"], record["id"])
        record["verified"] = (record["channel_id"] == target_meta["channel_id"]
                              and str(message.get("content", "")).strip() == content)
        save()
    if not receipts["romarrng_message"].get("verified"):
        raise DeliveryError("Discord accepted a link message requiring review; it was not reposted.")
    return receipts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("notes", "tag", "image", "release-url", "workflow-url", "receipt-file"):
        parser.add_argument("--" + field, required=True)
    args = parser.parse_args()
    names = ("DISCORD_RELEASE_WEBHOOK", "DISCORD_ROMARRNG_WEBHOOK")
    if any(not os.environ.get(name) for name in names):
        parser.error("DISCORD_RELEASE_WEBHOOK and DISCORD_ROMARRNG_WEBHOOK are required.")
    try:
        receipts = announce(
            notes=Path(args.notes).read_text(), tag=args.tag, image=args.image,
            release_url=args.release_url, workflow_url=args.workflow_url,
            changelog_webhook=os.environ[names[0]], romarrng_webhook=os.environ[names[1]],
            receipt_file=Path(args.receipt_file))
    except DeliveryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Changelog announcement:", receipts["changelog_messages"][0]["url"])
    print("ROMarrNG link post:", receipts["romarrng_message"]["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
