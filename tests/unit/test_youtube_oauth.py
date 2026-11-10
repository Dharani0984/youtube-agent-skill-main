import io
import json
import urllib.error
import unittest
from unittest.mock import patch

from telugu_shorts import youtube


class YouTubeOAuthTests(unittest.TestCase):
    def test_desktop_client_without_secret_omits_secret_parameter(self):
        fields = youtube._client_auth_fields({"client_id": "desktop-client-id"})
        self.assertEqual(fields, {"client_id": "desktop-client-id"})

    def test_client_secret_is_included_only_when_present(self):
        fields = youtube._client_auth_fields({
            "client_id": "desktop-client-id",
            "client_secret": "test-secret",
        })
        self.assertEqual(fields, {
            "client_id": "desktop-client-id",
            "client_secret": "test-secret",
        })

    def test_http_oauth_error_code_is_reported_without_response_details(self):
        body = json.dumps({
            "error": "invalid_client",
            "error_description": "invalid client configuration",
            "debug": "must not be displayed",
        }).encode("utf-8")
        response = io.BytesIO(body)
        error = urllib.error.HTTPError(
            "https://oauth2.googleapis.com/token", 401, "Unauthorized", {}, response
        )
        with patch.object(youtube.urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401, invalid_client") as caught:
                youtube._post_form(
                    youtube.TOKEN_URL,
                    b"client_id=desktop-client-id&code=authorization-code",
                )
        self.assertIn("invalid client configuration", str(caught.exception))
        self.assertNotIn("must not be displayed", str(caught.exception))
        self.assertNotIn("authorization-code", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
