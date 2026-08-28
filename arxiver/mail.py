"""Outbound email. Two backends, chosen by the EMAIL_BACKEND env var:

  console — dev default; writes the message to the app log so you can
            read the magic link without configuring a mail provider.
  resend  — production; posts to the Resend HTTP API.

Mirrors apps/server/src/email/sender.ts in puzzle-parlor so both apps
send through the same verified Resend domain with the same shape.
"""

import requests

from arxiver import app


class SendError(Exception):
    pass


def _send_console(to, subject, text, html=None):
    app.logger.info('\n=== [console email] to=%s subject=%r ===\n%s\n', to, subject, text)
    # Also to stdout so `docker compose logs -f app` shows it in dev.
    print('\n✉  [console] to=%s subject="%s"\n%s\n' % (to, subject, text), flush=True)
    return None


def _send_resend(to, subject, text, html=None):
    api_key = app.config.get('RESEND_API_KEY')
    if not api_key:
        raise SendError('RESEND_API_KEY required for the resend backend')
    body = {
        'from': app.config['EMAIL_FROM'],
        'to': [to],
        'subject': subject,
        'text': text,
    }
    if html:
        body['html'] = html
    resp = requests.post(
        'https://api.resend.com/emails',
        json=body,
        headers={'Authorization': 'Bearer ' + api_key},
        timeout=15,
    )
    if not resp.ok:
        raise SendError('resend failed: %s %s' % (resp.status_code, resp.text))
    return (resp.json() or {}).get('id')


def send(to, subject, text, html=None):
    """Deliver one message. Returns the provider message id, or None."""
    backend = app.config.get('EMAIL_BACKEND', 'console')
    if backend == 'resend':
        return _send_resend(to, subject, text, html)
    return _send_console(to, subject, text, html)
