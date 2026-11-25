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
    def test_cardmarket_guide_refreshes_when_published_newer(self):
        import hashlib,os,time
        from unittest.mock import MagicMock
        url="https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json"
        with tempfile.TemporaryDirectory() as directory:
            old=client.CACHE
            try:
                client.CACHE=Path(directory)
                file=client.CACHE/(hashlib.sha256(url.encode()).hexdigest()+".json")
                file.write_text(json.dumps({"createdAt":"old"}))
                two_hours_ago=time.time()-7200
                os.utime(file,(two_hours_ago,two_hours_ago))
                head=MagicMock(status_code=200,headers={"Last-Modified":"Wed, 25 Nov 2099 01:42:41 GMT"})
                get=MagicMock()
                get.return_value.__enter__.return_value=MagicMock(status_code=200,headers={"Content-Type":"application/json"},iter_content=lambda n:[b'{"createdAt":"new"}'])
                with patch.object(client.requests,"head",return_value=head),patch.object(client.requests,"get",get):
                    self.assertEqual(client.fetch_json(url)["createdAt"],"new")
                head.headers={"Last-Modified":"Wed, 25 Nov 2000 01:42:41 GMT"}
                os.utime(file,(two_hours_ago,two_hours_ago))
                with patch.object(client.requests,"head",return_value=head),patch.object(client.requests,"get",side_effect=AssertionError("network not allowed")):
                    self.assertEqual(client.fetch_json(url)["createdAt"],"new")
            finally:client.CACHE=old
if __name__=="__main__":unittest.main()
