"""Passwordless magic-link sign-in.

Ported from puzzle-parlor's apps/server/src/auth so both apps behave the
same way:

  * The raw token lives only in the emailed URL; the database stores a
    SHA-256 hash of it.
  * Links expire after 15 minutes and are single-use -- consumption is
    one atomic UPDATE, so two concurrent clicks can't both redeem it.
  * Requesting a link never reveals whether the address has an account.

Rate limiting is counted in the database rather than in process memory
(puzzle-parlor's approach) because arXiver runs under gunicorn with
several workers, and a per-process bucket would let each worker hand out
the full allowance.
"""

import datetime
import hashlib
import re
import secrets

from sqlalchemy import text

from arxiver import app, db, mail

TOKEN_TTL = datetime.timedelta(minutes=15)

# Per-window allowances, matched to puzzle-parlor's limiter: enough for
# someone who fat-fingers their address a few times, not enough to
# mail-bomb a stranger.
RATE_WINDOW = datetime.timedelta(minutes=10)
MAX_PER_IP = 5
MAX_PER_EMAIL = 3

# Deliberately loose -- real validation is "can they read the mail".
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def new_token():
    """43 characters of URL-safe base64 -- about 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def normalize_email(email):
    return (email or '').strip().lower()


def valid_email(email):
    return bool(EMAIL_RE.match(email or ''))


def client_ip(request):
    """Best-effort client IP for rate-limit bucketing.

    Trust order matches puzzle-parlor: Cloudflare's own header first (it
    can't be spoofed by the client), then the *last* X-Forwarded-For hop
    -- earlier hops are client-supplied, so taking the first would let a
    caller rotate fake IPs straight past the limiter.
    """
    cf = request.headers.get('CF-Connecting-IP')
    if cf:
        return cf.strip()[:64]
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        return (xff.split(',')[-1].strip() or 'unknown')[:64]
    real = request.headers.get('X-Real-IP')
    if real:
        return real.strip()[:64]
    return (request.remote_addr or 'unknown')[:64]


def safe_next(target):
    """Only relative, same-site paths survive.

    ``//evil.com`` is a protocol-relative URL, not a local path, so it is
    rejected along with anything carrying a scheme.
    """
    if not target or not target.startswith('/') or target.startswith('//'):
        return None
    if '\\' in target or '\n' in target or '\r' in target:
        return None
    return target


def _recent(column, value, since):
    from arxiver.models import AuthToken
    return AuthToken.query.filter(
        column == value, AuthToken.created >= since
    ).count()


def rate_limited(email, ip):
    from arxiver.models import AuthToken
    since = datetime.datetime.utcnow() - RATE_WINDOW
    if _recent(AuthToken.requester_ip, ip, since) >= MAX_PER_IP:
        return True
    if _recent(AuthToken.email, email, since) >= MAX_PER_EMAIL:
        return True
    return False


def issue(email, ip, next_url=None):
    """Create a token and mail the link. Returns True if a link was sent.

    Callers must report success to the user either way -- see the login
    view -- so that a probe can't tell a rate-limited address from a
    fresh one.
    """
    from arxiver.models import AuthToken

    token = new_token()
    now = datetime.datetime.utcnow()
    db.session.add(AuthToken(
        token_hash=hash_token(token),
        email=email,
        created=now,
        expires=now + TOKEN_TTL,
        requester_ip=ip,
        next_url=safe_next(next_url),
    ))
    db.session.commit()

    url = '%s/auth/verify?token=%s' % (app.config['APP_URL'].rstrip('/'), token)
    subject, body, html = render(url)
    try:
        mail.send(email, subject, body, html)
    except Exception:
        # Swallow the failure so the response is identical for addresses
        # the provider rejects. The row is already written, so a link can
        # still be recovered from the logs by hand if it matters.
        app.logger.exception('magic link send failed for %s', email)
        return False
    return True


def consume(token):
    """Redeem a token, returning ``(email, next_url)`` or ``(None, None)``.

    The UPDATE both checks the token is unused and unexpired *and* marks
    it spent, in one statement. A SELECT-then-UPDATE would let two
    simultaneous clicks on the same link each mint a session.
    """
    if not token:
        return None, None
    row = db.session.execute(
        text('UPDATE auth_token SET used_at = :now'
             ' WHERE token_hash = :h AND used_at IS NULL AND expires > :now'
             ' RETURNING email, next_url'),
        {'h': hash_token(token), 'now': datetime.datetime.utcnow()},
    ).first()
    db.session.commit()
    if row is None:
        return None, None
    return row[0], row[1]


def purge_expired():
    """Drop spent and expired rows. Called opportunistically on login."""
    from arxiver.models import AuthToken
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    AuthToken.query.filter(AuthToken.expires < cutoff).delete(synchronize_session=False)
    db.session.commit()


def render(url):
    """Subject, plain-text and HTML bodies for the sign-in email."""
    subject = 'Your arXiver sign-in link'
    text_body = '\n'.join([
        'Sign in to arXiver.',
        '',
        'Click to sign in:',
        url,
        '',
        "This link expires in 15 minutes. If you didn't request it, just ignore this email.",
    ])

    # Inline styles only -- mail clients strip <style> blocks. #428bca is
    # the Bootstrap primary the site itself uses.
    html_body = """<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;color:#333;">
    <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" style="background:#f5f5f5;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" style="max-width:480px;background:#ffffff;border:1px solid #e3e3e3;border-radius:6px;padding:32px 28px 24px 28px;">
            <tr>
              <td style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#428bca;">
                arXiver
              </td>
            </tr>
            <tr>
              <td style="font-size:24px;line-height:1.2;color:#333;padding-top:6px;padding-bottom:8px;">
                Your sign-in link
              </td>
            </tr>
            <tr>
              <td style="font-size:14px;line-height:1.55;color:#666;padding-bottom:24px;">
                Click the button below to sign in. The link is good for 15 minutes; after that you'll need to request a new one.
              </td>
            </tr>
            <tr>
              <td style="padding-bottom:8px;">
                <a href="%(url)s" style="display:inline-block;padding:12px 24px;border-radius:4px;background:#428bca;color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;">
                  Sign in to arXiver
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:18px;font-size:12px;color:#888;line-height:1.5;">
                Or paste this URL into your browser:<br>
                <a href="%(url)s" style="color:#428bca;word-break:break-all;">%(url)s</a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:24px;border-top:1px solid #eee;font-size:11px;color:#999;line-height:1.5;">
                Didn't request this? Just ignore the email &mdash; no account is created until you click the link.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>""" % {'url': url}

    return subject, text_body, html_body
