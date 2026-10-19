#!/usr/bin/env python
"""Run one arXiv harvest in this process.

    python harvest.py          # incremental, from the last checkpoint
    python harvest.py --all    # walk the whole archive

This replaces the /update endpoint's thread. A harvest inside a gunicorn
worker starved request handling -- a 46-day catch-up made the site serve
white pages, because requests routed to the worker whose GIL the harvest
held could not complete. Run from the cron container, which shares the code
and the database but serves no traffic.
"""

import sys
import traceback

from arxiver import app, db
from arxiver import harvest_state
from arxiver.updater import Updater


def main(argv):
    update_all = '--all' in argv
    with app.app_context():
        claimed, state = harvest_state.claim_slot(logger=app.logger)
        if not claimed:
            print('harvest already running since %s (pid %s on %s); not starting another.'
                  % (state.get('started'), state.get('pid'), state.get('host')))
            return 0
        print('harvest started%s' % (' (full archive)' if update_all else ''))
        try:
            count = Updater().run(update_all=update_all)
        except Exception:
            tb = traceback.format_exc()
            harvest_state.finish_slot(error=tb, logger=app.logger)
            db.session.rollback()
            print(tb, file=sys.stderr)
            return 1
        harvest_state.finish_slot(count=count, logger=app.logger)
        print('harvest finished: %d records added/updated' % count)
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
