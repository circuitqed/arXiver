# !/usr/local/bin/python

__author__ = 'dave'

from sickle import Sickle
import datetime, dateutil
from arxiver.models import Article, Author, Category, Synchronization
from arxiver import db
from flask.ext.script import Command, Option


class Updater(Command):
    def __init__(self, default_update_all=False):
        self.default_update_all = default_update_all

    def get_options(self):
        return [
            Option('-u', '--update_all', dest='update_all', default=self.default_update_all),
        ]

    def run(self, update_all=False, override=False):
        arxiv = Sickle('http://export.arxiv.org/oai2')

        # date = datetime.date(2014, 5, 14)
        # records = arxiv.ListRecords(**{'metadataPrefix': 'arXiv', 'from': str(date)})
        # print str(datetime.date(2014, 5, 14))
        last_update = Synchronization.query.order_by(Synchronization.id.desc()).first()
        if (datetime.datetime.utcnow() - last_update.date).days < 1:
            return 0

        if last_update is None or update_all:
            date = None
            records = arxiv.ListRecords(metadataPrefix='arXiv')
        else:
            date = last_update.date.date()
            records = arxiv.ListRecords(**{'metadataPrefix': 'arXiv', 'from': str(date)})

        count = 0
        badrecords = []
        for r in records:
            count += 1
            if count % 1000 == 0: print count
            try:
                a = self.add_article(r.metadata)
            except Exception as e:
                badrecords.append(r)
                print "Exception: ", e
            # print a.title
            db.session.commit()
        db.session.add(Synchronization(date=datetime.datetime.now()))
        db.session.commit()
        print "all done!"
        return count

    def add_category(self, name):
        c = Category.query.filter_by(name=name).first()
        if c is None:
            c = Category(name=name)
            db.session.add(c)
        return c

    def add_author(self, forenames, lastname):
        a = Author.query.filter_by(forenames=forenames, lastname=lastname).first()
        if a is None:
            a = Author(forenames=forenames, lastname=lastname)
            db.session.add(a)
        return a

    def add_article(self, metadata):
        if 'doi' not in metadata: metadata['doi'] = ['']
        if 'journal-ref' not in metadata: metadata['journal-ref'] = ['']
        if 'msc-class' not in metadata: metadata['msc-class'] = ['']
        if 'acm-class' not in metadata: metadata['acm-class'] = ['']
        if 'comments' not in metadata: metadata['comments'] = ['']
        if 'license' not in metadata: metadata['license'] = ['']
        if 'forenames' not in metadata: metadata['forenames'] = ['' for n in metadata['keyname']]

        a = Article.query.filter_by(arxiv_id=metadata['id'][0]).first()
        if a is not None:
            return a

        created_dt = datetime.datetime.strptime(metadata['created'][0], '%Y-%m-%d')
        if 'updated' in metadata:
            updated_dt = datetime.datetime.strptime(metadata['updated'][0], '%Y-%m-%d')
        else:
            updated_dt = None

        a = Article(title=metadata['title'][0], abstract=metadata['abstract'][0],
                    arxiv_id=metadata['id'][0],
                    created=created_dt, updated=updated_dt,
                    doi=metadata['doi'][0], journalref=metadata['journal-ref'][0],
                    mscclass=metadata['msc-class'][0], acmclass=metadata['acm-class'][0],
                    comments=metadata['comments'][0], license=metadata['license'][0])
        if 'categories' in metadata:
            for catname in metadata['categories'][0].split(' '):
                category = self.add_category(catname)
                a.categories.append(category)

        a_str = u""
        for fname, lname in zip(metadata['forenames'], metadata['keyname']):
            author = self.add_author(fname, lname)
            a_str += author.__repr__() + ' '
            if author not in a.authors:
                a.authors.append(author)

        a.full_description = metadata['title'][0] + '\n' + a_str[:-1] + '\n' + metadata['abstract'][0] + '\n' + \
                             metadata['id'][0] + '\n' + metadata['categories'][0]

        db.session.add(a)
        return a


def do_update(update_all=False):
    u = Updater()
    return u.run(update_all=update_all)


if __name__ == '__main__':
    do_update()
