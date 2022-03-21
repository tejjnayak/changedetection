#!/usr/bin/python3
"""Test suite for the render/not render anchor tag content functionality"""

import time
from flask import url_for
from .util import live_server_setup

import multiprocessing
multiprocessing.set_start_method('fork')

def test_setup(live_server):
    live_server_setup(live_server)


def set_original_ignore_response():
    test_return_data = """<html>
       <body>
     Some initial text</br>
     <a href="/original_link"> Some More Text </a>
     </br>
     So let's see what happens.  </br>
     </body>
     </html>
    """

    with open("test-datastore/endpoint-content.txt", "w") as f:
        f.write(test_return_data)


# Should be the same as set_original_ignore_response() but with a different
# link
def set_modified_ignore_response():
    test_return_data = """<html>
       <body>
     Some initial text</br>
     <a href="/modified_link"> Some More Text </a>
     </br>
     So let's see what happens.  </br>
     </body>
     </html>
    """

    with open("test-datastore/endpoint-content.txt", "w") as f:
        f.write(test_return_data)

def test_render_anchor_tag_content_true(client, live_server):
    """Testing that the link changes are detected when functionality is
    detected"""
    sleep_time_for_fetch_thread = 3

    # Give the endpoint time to spin up
    time.sleep(1)

    # set original html text
    set_original_ignore_response()

    # Goto the settings page, choose not to ignore links
    res = client.post(
        url_for("settings_page"),
        data={
            "minutes_between_check": 180,
            "render_anchor_tag_content": "true",
            "fetch_backend": "html_requests",
        },
        follow_redirects=True,
    )
    assert b"Settings updated." in res.data

    # Add our URL to the import page
    test_url = url_for("test_endpoint", _external=True)
    res = client.post(
        url_for("import_page"), data={"urls": test_url},
        follow_redirects=True
    )
    assert b"1 Imported" in res.data

    time.sleep(sleep_time_for_fetch_thread)
    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # set a new html text with a modified link
    set_modified_ignore_response()
    time.sleep(sleep_time_for_fetch_thread)

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(sleep_time_for_fetch_thread)

    # since the link has changed, and we chose to render anchor tag content,
    # we should detect a change (new 'unviewed' class)
    res = client.get(url_for("index"))
    assert b"unviewed" in res.data
    assert b"/test-endpoint" in res.data

    # Cleanup everything
    res = client.get(url_for("api_delete", uuid="all"),
                     follow_redirects=True)
    assert b'Deleted' in res.data


def test_render_anchor_tag_content_false(client, live_server):
    """Testing that anchor tag content changes are ignored when the option is
    selected"""
    sleep_time_for_fetch_thread = 3

    # Give the endpoint time to spin up
    time.sleep(1)

    # set the original html text
    set_original_ignore_response()

    # Goto the settings page, choose to ignore hyperlinks
    res = client.post(
        url_for("settings_page"),
        data={
            "minutes_between_check": 180,
            "render_anchor_tag_content": "false",
            "fetch_backend": "html_requests",
        },
        follow_redirects=True,
    )
    assert b"Settings updated." in res.data

    # Add our URL to the import page
    test_url = url_for("test_endpoint", _external=True)
    res = client.post(
        url_for("import_page"), data={"urls": test_url}, follow_redirects=True
    )
    assert b"1 Imported" in res.data

    time.sleep(sleep_time_for_fetch_thread)
    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # set a new html text, with a modified link
    set_modified_ignore_response()
    time.sleep(sleep_time_for_fetch_thread)

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(sleep_time_for_fetch_thread)

    # even though the link has changed, we shouldn't detect a change since
    # we selected to not render anchor tag content (no new 'unviewed' class)
    res = client.get(url_for("index"))
    assert b"unviewed" not in res.data
    assert b"/test-endpoint" in res.data

    # Cleanup everything
    res = client.get(url_for("api_delete", uuid="all"), follow_redirects=True)
    assert b'Deleted' in res.data
