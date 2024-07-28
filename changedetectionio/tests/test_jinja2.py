#!/usr/bin/env python3

import time
from flask import url_for
from .util import live_server_setup, wait_for_all_checks
from ..safe_jinja import render


def test_setup(client, live_server, measure_memory_usage):
    live_server_setup(live_server)

# If there was only a change in the whitespacing, then we shouldnt have a change detected
def test_jinja2_in_url_query(client, live_server, measure_memory_usage):
    #live_server_setup(live_server)

    # Add our URL to the import page
    test_url = url_for('test_return_query', _external=True)

    # because url_for() will URL-encode the var, but we dont here
    full_url = "{}?{}".format(test_url,
                              "date={% now 'Europe/Berlin', '%Y' %}.{% now 'Europe/Berlin', '%m' %}.{% now 'Europe/Berlin', '%d' %}", )
    res = client.post(
        url_for("form_quick_watch_add"),
        data={"url": full_url, "tags": "test"},
        follow_redirects=True
    )
    assert b"Watch added" in res.data
    wait_for_all_checks(client)

    # It should report nothing found (no new 'unviewed' class)
    res = client.get(
        url_for("preview_page", uuid="first"),
        follow_redirects=True
    )
    assert b'date=2' in res.data

# https://techtonics.medium.com/secure-templating-with-jinja2-understanding-ssti-and-jinja2-sandbox-environment-b956edd60456
def test_jinja2_security_url_query(client, live_server, measure_memory_usage):
    #live_server_setup(live_server)

    # Add our URL to the import page
    test_url = url_for('test_return_query', _external=True)

    # because url_for() will URL-encode the var, but we dont here
    full_url = "{}?{}".format(test_url,
                              "date={{ ''.__class__.__mro__[1].__subclasses__()}}", )
    res = client.post(
        url_for("form_quick_watch_add"),
        data={"url": full_url, "tags": "test"},
        follow_redirects=True
    )
    assert b"Watch added" in res.data
    wait_for_all_checks(client)

    # It should report nothing found (no new 'unviewed' class)
    res = client.get(url_for("index"))
    assert b'is invalid and cannot be used' in res.data
    # Some of the spewed output from the subclasses
    assert b'dict_values' not in res.data

def test_add_time(environment):
    """Verify that added time offset can be parsed."""

    finalRender = render("{% now 'utc' + 'hours=2,seconds=30' %}")

    assert finalRender == "Thu, 10 Dec 2015 01:33:31"


def test_substract_time(environment):
    """Verify that substracted time offset can be parsed."""

    finalRender = render("{% now 'utc' - 'minutes=11' %}")

    assert finalRender == "Wed, 09 Dec 2015 23:22:01"


def test_offset_with_format(environment):
    """Verify that offset works together with datetime format."""

    finalRender = render(
        "{% now 'utc' - 'days=2,minutes=33,seconds=1', '%d %b %Y %H:%M:%S' %}"
    )

    assert finalRender == "07 Dec 2015 23:00:00"