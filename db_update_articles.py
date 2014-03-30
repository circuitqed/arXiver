#!/usr/local/bin/python

__author__ = 'dave'

from sickle import Sickle
import datetime, dateutil
from arxiver.models import Article, Author, Category
from arxiver import db


def add_category(name):
    c = Category.query.filter_by(name=name).first()
    if c is None:
        c = Category(name=name)
        db.session.add(c)
    return c


def add_author(forenames, lastname):
    a = Author.query.filter_by(forenames=forenames, lastname=lastname).first()
    if a is None:
        a = Author(forenames=forenames, lastname=lastname)
        db.session.add(a)
    return a


def add_article(metadata):
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
            category = add_category(catname)
            a.categories.append(category)

    for fname, lname in zip(metadata['forenames'], metadata['keyname']):
        author = add_author(fname, lname)
        if author not in a.authors:
            a.authors.append(author)

    db.session.add(a)
    return a


if __name__=='__main__':

    arxiv = Sickle('http://export.arxiv.org/oai2')

    date = datetime.date(2014, 2, 14)

    records = arxiv.ListRecords(**{'metadataPrefix': 'arXiv', 'from': str(date)})
    #records = arxiv.ListRecords(metadataPrefix= 'arXiv')

    count=0
    badrecords=[]
    for r in records:
        count+=1
        if count % 1000==0: print count
        try:
            a = add_article(r.metadata)
        except Exception as e:
            badrecords.append(r)
            print "Exception: ", e
        #print a.title
        if count == 5180:
            print r.metadata
            db.engine.echo=True
            db.session.commit()
            db.engine.echo=False
        db.session.commit()
