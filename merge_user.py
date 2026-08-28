#!/usr/bin/env python
"""Fold a legacy Google account into a magic-link account.

The old OAuth flow never stored an email address, so a user who signs in
with a magic link gets a brand-new account and leaves their old feeds
behind. This moves the feeds, subscriptions and likes across, then
deactivates the old row.

    docker compose exec app python merge_user.py --list
    docker compose exec app python merge_user.py --from 2 --to 1
    docker compose exec app python merge_user.py --from 2 --to 1 --commit

Nothing is written without --commit.
"""

import argparse
import sys

from arxiver import db
from arxiver.models import User, Feed, Subscription, articlelikes


def show_users():
    rows = User.query.order_by(User.id).all()
    print('%3s  %-22s %-24s %-22s %s' % ('id', 'fullname', 'email', 'nickname', 'feeds'))
    for u in rows:
        print('%3d  %-22s %-24s %-22s %d' % (
            u.id, (u.fullname or '')[:22], (u.email or '-')[:24],
            (u.nickname or '-')[:22], u.feeds.count()))


def merge(src_id, dst_id, commit):
    src = User.query.get(src_id)
    dst = User.query.get(dst_id)
    if src is None or dst is None:
        sys.exit('no such user: %s' % (src_id if src is None else dst_id))
    if src.id == dst.id:
        sys.exit('source and destination are the same account')

    feeds = Feed.query.filter_by(owner_id=src.id).all()
    subs = Subscription.query.filter_by(user_id=src.id).all()
    likes = db.session.execute(
        articlelikes.select().where(articlelikes.c.user_id == src.id)).fetchall()

    print('from: %s (id=%s, username=%s, email=%s)' % (
        src.fullname, src.id, src.username, src.email))
    print('  to: %s (id=%s, email=%s)' % (dst.fullname, dst.id, dst.email))
    print('moving %d feed(s), %d subscription(s), %d like(s)' % (
        len(feeds), len(subs), len(likes)))
    for f in feeds:
        print('  feed %s: %s' % (f.id, f.name))

    if not commit:
        print('\ndry run -- pass --commit to apply')
        return

    for f in feeds:
        f.owner_id = dst.id
    # A subscription the destination already holds would violate nothing
    # at the database level but would show the feed twice, so drop the
    # duplicate rather than move it.
    existing = {s.feed_id for s in Subscription.query.filter_by(user_id=dst.id)}
    for s in subs:
        if s.feed_id in existing:
            db.session.delete(s)
        else:
            s.user_id = dst.id
    for row in likes:
        dupe = db.session.execute(articlelikes.select().where(
            (articlelikes.c.user_id == dst.id) &
            (articlelikes.c.article_id == row.article_id))).first()
        if dupe is None:
            db.session.execute(articlelikes.update().where(
                (articlelikes.c.user_id == src.id) &
                (articlelikes.c.article_id == row.article_id)
            ).values(user_id=dst.id))
        else:
            db.session.execute(articlelikes.delete().where(
                (articlelikes.c.user_id == src.id) &
                (articlelikes.c.article_id == row.article_id)))

    # Keep the row for provenance, but make sure nobody can sign into it.
    src.active = False
    if src.fullname and (not dst.fullname or dst.fullname == (dst.email or '').split('@')[0]):
        dst.fullname = src.fullname
    if src.avatar and not dst.avatar:
        dst.avatar = src.avatar
    db.session.commit()
    print('merged.')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', action='store_true', help='show all accounts and exit')
    ap.add_argument('--from', dest='src', type=int, help='legacy account id to drain')
    ap.add_argument('--to', dest='dst', type=int, help='magic-link account id to keep')
    ap.add_argument('--commit', action='store_true', help='actually write the changes')
    args = ap.parse_args()

    if args.list or args.src is None or args.dst is None:
        show_users()
        if not args.list:
            print('\npass --from <id> --to <id> to merge')
        return
    merge(args.src, args.dst, args.commit)


if __name__ == '__main__':
    main()
