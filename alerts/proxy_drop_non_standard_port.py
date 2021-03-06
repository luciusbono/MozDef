#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# Copyright (c) 2014 Mozilla Corporation


from lib.alerttask import AlertTask
from query_models import QueryStringMatch, SearchQuery, TermMatch


class AlertProxyDropNonStandardPort(AlertTask):
    def main(self):
        self.parse_config(
            'proxy_drop_non_standard_port.conf', ['excludedports'])

        search_query = SearchQuery(minutes=20)

        search_query.add_must([
            TermMatch('category', 'squid'),
            TermMatch('tags', 'squid'),
            TermMatch('details.proxyaction', 'TCP_DENIED/-'),
            TermMatch('details.tcpaction', 'CONNECT')
        ])

        # Only notify on certain ports from config
        port_regex = "/.*:({0})/".format(
            self.config.excludedports.replace(',', '|'))
        search_query.add_must_not([
            QueryStringMatch('details.destination: {}'.format(port_regex))
        ])

        self.filtersManual(search_query)

        # Search aggregations on field 'hostname', keep X samples of
        # events at most
        self.searchEventsAggregated('details.sourceipaddress', samplesLimit=10)
        # alert when >= X matching events in an aggregation
        # I think it makes sense to alert every time here
        self.walkAggregations(threshold=1)

        # Set alert properties
    def onAggregation(self, aggreg):
         # aggreg['count']: number of items in the aggregation, ex: number of failed login attempts
         # aggreg['value']: value of the aggregation field, ex: toto@example.com
         # aggreg['events']: list of events in the aggregation
        category = 'squid'
        tags = ['squid', 'proxy']
        severity = 'WARNING'

        destinations = set()
        for event in aggreg['allevents']:
            destinations.add(event['_source']['details']['destination'])

        summary = 'Suspicious Proxy DROP event(s) detected from {0} to the following non-std port destination(s): {1}'.format(
            aggreg['value'],
            ",".join(sorted(destinations))
        )

        # Create the alert object based on these properties
        return self.createAlertDict(summary, category, tags, aggreg['events'], severity)
