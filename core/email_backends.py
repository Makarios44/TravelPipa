"""
E-mail backend that sends through the Resend HTTPS API (https://resend.com).

Railway blocks outbound SMTP (ports 25/465/587) on its Free, Trial and Hobby
plans, so the site sends its notifications over HTTPS instead. No extra Python
package is needed: the request is made with the standard library.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, api_key=None, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or settings.RESEND_API_KEY
        self.timeout = timeout or getattr(settings, "EMAIL_TIMEOUT", 15)

    def _payload(self, message):
        data = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            data["cc"] = list(message.cc)
        if message.bcc:
            data["bcc"] = list(message.bcc)
        if message.reply_to:
            data["reply_to"] = list(message.reply_to)
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                data["html"] = content
        return data

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not configured.")
            return 0
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            request = urllib.request.Request(
                RESEND_ENDPOINT,
                data=json.dumps(self._payload(message)).encode(),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                         "User-Agent": "TravelPipa/1.0"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response.read()
                sent += 1
            except urllib.error.HTTPError as exc:
                detail = exc.read()[:500].decode("utf-8", "replace")
                logger.error("Resend rejected the e-mail (%s): %s", exc.code, detail)
                if not self.fail_silently:
                    raise
            except (urllib.error.URLError, TimeoutError, OSError):
                logger.exception("Could not reach the Resend API")
                if not self.fail_silently:
                    raise
        return sent
