# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Aurélien Bompard <abompard@fedoraproject.org>
Author: Aurélien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import

import datetime

from kittystore import MessageNotFound
from kittystore.utils import get_message_id_hash, parseaddr, parsedate
from kittystore.utils import header_to_unicode, payload_to_unicode
from kittystore.utils import get_ref_and_thread_id

from zope.interface import implements
from mailman.interfaces.messages import IMessageStore
from storm.locals import *

from .model import List, Email

#from kittystore.sa.kittysamodel import get_class_object
#from sqlalchemy import create_engine, distinct, MetaData, and_, desc, or_
#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy.orm import sessionmaker
#from sqlalchemy.orm.exc import NoResultFound


class StormStore(object):
    """
    Storm-powered interface to query emails from the database.
    """

    implements(IMessageStore)

    def __init__(self, db, debug=False):
        """ Constructor.
        Create the session using the engine defined in the url.

        :param db: the Storm store object
        :param debug: a boolean to set the debug mode on or off.
        """
        self.db = db

    def add(self, message):
        """Add the message to the store.

        :param message: An email.message.Message instance containing at
            least a unique Message-ID header.  The message will be given
            an X-Message-ID-Hash header, overriding any existing such
            header.
        :returns: The calculated X-Message-ID-Hash header.
        :raises ValueError: if the message is missing a Message-ID 
            header.
            The storage service is also allowed to raise this exception
            if it find, but disallows collisions.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def add_to_list(self, list_name, message):
        """Add the message to a specific list of the store.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message: An email.message.Message instance containing at
            least a unique Message-ID header.  The message will be given
            an X-Message-ID-Hash header, overriding any existing such
            header.
        :returns: The calculated X-Message-ID-Hash header.
        :raises ValueError: if the message is missing a Message-ID 
            header.
            The storage service is also allowed to raise this exception
            if it find, but disallows collisions.
        """
        # Create the list if it does not exist
        list_is_in_db = self.db.find(List,
                List.name == unicode(list_name)).count()
        if not list_is_in_db:
            self.db.add(List(list_name))
        if not message.has_key("Message-Id"):
            raise ValueError("No 'Message-Id' header in email", message)
        msg_id = message['Message-Id'].strip("<>")
        email = Email(list_name, msg_id)
        if self.is_message_in_list(list_name, email.message_id):
            print ("Duplicate email from %s: %s" %
                   (message['From'], message.get('Subject', '""')))
            return email.hash_id

        # Find thread id
        ref, thread_id = get_ref_and_thread_id(message, list_name, self)
        if thread_id is None:
            # make up the thread_id if not found
            thread_id = email.hash_id
        email.thread_id = thread_id
        email.in_reply_to = ref

        from_name, from_email = parseaddr(message['From'])
        from_name = header_to_unicode(from_name)
        email.sender_name = from_name
        email.sender_email = unicode(from_email)
        email.subject = header_to_unicode(message.get('Subject'))
        payload = payload_to_unicode(message)
        email.content = payload
        email.date = parsedate(message.get("Date"))
        email.full = message.as_string()

        #category = 'Question' # TODO: enum + i18n ?
        #if ('agenda' in message.get('Subject', '').lower() or
        #        'reminder' in message.get('Subject', '').lower()):
        #    # i18n!
        #    category = 'Agenda'

        self.db.add(email)
        self.flush()
        return email.hash_id

    def delete_message(self, message_id):
        """Remove the given message from the store.

        :param message: The Message-ID of the mesage to delete from the
            store.
        :raises LookupError: if there is no such message.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def delete_message_from_list(self, list_name, message_id):
        """Remove the given message for a specific list from the store.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message: The Message-ID of the mesage to delete from the
            store.
        :raises LookupError: if there is no such message.
        """
        msg = self.get_message_by_id_from_list(list_name, message_id)
        if msg is None:
            raise MessageNotFound(list_name, message_id)
        self.db.delete(msg)
        self.flush()

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        return self.db.find(Email,
                Email.list_name == unicode(list_name)).count()


    def get_message_by_hash(self, message_id_hash):
        """Return the message with the matching X-Message-ID-Hash.

        :param message_id_hash: The X-Message-ID-Hash header contents to
            search for.
        :returns: The message, or None if no matching message was found.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def get_message_by_hash_from_list(self, list_name, message_id_hash):
        """Return the message with the matching X-Message-ID-Hash.

        :param message_id_hash: The X-Message-ID-Hash header contents to
            search for.
        :returns: The message, or None if no matching message was found.
        """
        return self.db.find(Email,
                Email.hash_id == unicode(message_id_hash)).one()

    def get_message_by_id(self, message_id):
        """Return the message with a matching Message-ID.

        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def get_message_by_id_from_list(self, list_name, message_id):
        """Return the message with a matching Message-ID.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        msg = self.db.find(Email,
                Email.message_id == unicode(message_id)).one()
        return msg

    def is_message_in_list(self, list_name, message_id):
        """Return the number of messages with a matching Message-ID in the list.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        return self.db.find(Email.message_id,
                Email.message_id == unicode(message_id)).count()

    def search_list_for_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :param list_name: name of the mailing list in which this email
        should be searched.
        :param keyword: keyword to search in the content of the emails.
        """
        emails = self.db.find(Email,
                Email.content.ilike(u'%{0}%'.format(keyword))
                ).order_by(Desc(Email.date))
        return emails

    def search_list_for_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the content or subject of
            the emails.
        """
        emails = self.db.find(Email, Or(
                    Email.content.ilike(u'%{0}%'.format(keyword)),
                    Email.subject.ilike(u'%{0}%'.format(keyword)),
                )).order_by(Desc(Email.date))
        return emails

    def search_list_for_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the database.
        """
        emails = self.db.find(Email, Or(
                    Email.sender_name.ilike(u'%{0}%'.format(keyword)),
                    Email.sender_email.ilike(u'%{0}%'.format(keyword)),
                )).order_by(Desc(Email.date))
        return emails

    def search_list_for_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the subject of the emails.
        """
        emails = self.db.find(Email,
                Email.subject.ilike(u'%{0}%'.format(keyword)),
                ).order_by(Desc(Email.date))
        return emails

    @property
    def messages(self):
        """An iterator over all messages in this message store."""
        raise NotImplementedError




    def get_list_names(self):
        """Return the names of the archived lists.

        :returns: A list containing the names of the archived mailing-lists.
        """
        return list(self.db.find(List.name).order_by(List.name))

    def get_archives(self, list_name, start, end):
        """ Return all the thread-starting emails between two given dates.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg start, a datetime object representing the starting date of
        the interval to query.
        :arg end, a datetime object representing the ending date of
        the interval to query.
        """
        # Beginning of thread == No 'References' header
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.in_reply_to == None,
                    Email.date >= start,
                    Email.date <= end,
                )).order_by(Desc(Email.date))
        return list(emails)

    def get_archives_length(self, list_name):
        """ Return a dictionnary of years, months for which there are
        potentially archives available for a given list (based on the
        oldest post on the list).

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        archives = {}
        first = self.db.find(Email.date,
                Email.list_name == unicode(list_name)
                ).order_by(Email.date)[:1]
        if not list(first):
            return archives
        else:
            first = first.one()
        now = datetime.datetime.now()
        year = first.year
        month = first.month
        while year < now.year:
            archives[year] = range(1, 13)[(month -1):]
            year = year + 1
            month = 1
        archives[now.year] = range(1, 13)[:now.month]
        return archives

    def get_thread(self, list_name, thread_id):
        """ Return all the emails present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, thread_id as used in the web-pages.
        Used here to uniquely identify the thread in the database.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.thread_id == unicode(thread_id),
                )).order_by(Desc(Email.date))
        return list(emails)

    def get_thread_length(self, list_name, thread_id):
        """ Return the number of email present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        return self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.thread_id == unicode(thread_id),
                )).count()

    def get_thread_participants(self, list_name, thread_id):
        """ Return the list of participant in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        participants = self.db.find(Email.sender_name, And(
                    Email.list_name == unicode(list_name),
                    Email.thread_id == unicode(thread_id),
                )).config(distinct=True)
        return list(participants)

    def flush(self):
        self.db.flush()

    def commit(self):
        self.db.commit()