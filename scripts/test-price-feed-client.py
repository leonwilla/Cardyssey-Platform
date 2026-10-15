#!/usr/bin/env python3
"""Unit tests for shared DE/EN price-feed transport (no live requests)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import price_feed_client as client

class FeedTests(unittest.TestCase):
    def test_host_restriction(self):
        with self.assertRaises(ValueError):
            client.fetch_json("https://localhost/private")
        with self.assertRaises(ValueError):
            client.fetch_json("https://tcgcsv.com:444/tcgplayer/3/groups")
        with self.assertRaises(ValueError):
            client.fetch_json("http://tcgcsv.com/tcgplayer/3/groups")

    def test_cached_feed_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            import hashlib
            url="https://tcgcsv.com/tcgplayer/3/groups"
            old=client.CACHE
            try:
                client.CACHE=Path(directory)
                file=client.CACHE/(hashlib.sha256(url.encode()).hexdigest()+".json")
                file.write_text(json.dumps({"results":[{"groupId":1}]}))
                with patch.object(client.requests,"get",side_effect=AssertionError("network not allowed")):
                    result=client.fetch_json(url)
                self.assertEqual(result["results"][0]["groupId"],1)
            finally:client.CACHE=old
if __name__=="__main__":unittest.main()
