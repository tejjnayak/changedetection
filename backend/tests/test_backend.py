#!/usr/bin/python3

import time
from flask import url_for
from urllib.request import urlopen
import pytest

sleep_time_for_fetch_thread = 3


def test_setup_liveserver(live_server):
    @live_server.app.route('/test-endpoint')
    def test_endpoint():
        # Tried using a global var here but didn't seem to work, so reading from a file instead.
        with open("test-datastore/output.txt", "r") as f:
            return f.read()


    @live_server.app.route('/test_notification_endpoint', methods=['POST'])
    def test_notification_endpoint():
        with open("test-datastore/count.txt", "w") as f:
            f.write("we hit it")
        return "alright, you hit it"

    # And this should return not zero.
    @live_server.app.route('/test_notification_counter')
    def test_notification_counter():
        with open("test-datastore/count.txt", "r") as f:
            return f.read()
    live_server.start()

    assert 1 == 1


def set_original_response():
    test_return_data = """<html>
       <body>
     Some initial text</br>
     <p>Which is across multiple lines</p>
     </br>
     So let's see what happens.  </br>
     </body>
     </html>
    """

    with open("test-datastore/output.txt", "w") as f:
        f.write(test_return_data)


def set_modified_response():
    test_return_data = """<html>
       <body>
     Some initial text</br>
     <p>which has this one new line</p>
     </br>
     So let's see what happens.  </br>
     </body>
     </html>
    """

    with open("test-datastore/output.txt", "w") as f:
        f.write(test_return_data)


def test_check_basic_change_detection_functionality(client, live_server):
    set_original_response()

    # Add our URL to the import page
    res = client.post(
        url_for("import_page"),
        data={"urls": url_for('test_endpoint', _external=True)},
        follow_redirects=True
    )
    assert b"1 Imported" in res.data

    time.sleep(sleep_time_for_fetch_thread)

    # Do this a few times.. ensures we dont accidently set the status
    for n in range(3):
        client.get(url_for("api_watch_checknow"), follow_redirects=True)

        # Give the thread time to pick it up
        time.sleep(sleep_time_for_fetch_thread)

        # It should report nothing found (no new 'unviewed' class)
        res = client.get(url_for("index"))
        assert b'unviewed' not in res.data
        assert b'test-endpoint' in res.data

        # Default no password set, this stuff should be always available.

        assert b"SETTINGS" in res.data
        assert b"BACKUP" in res.data
        assert b"IMPORT" in res.data

    #####################

    # Make a change
    set_modified_response()

    res = urlopen(url_for('test_endpoint', _external=True))
    assert b'which has this one new line' in res.read()

    # Force recheck
    res = client.get(url_for("api_watch_checknow"), follow_redirects=True)
    assert b'1 watches are rechecking.' in res.data

    time.sleep(sleep_time_for_fetch_thread)

    # Now something should be ready, indicated by having a 'unviewed' class
    res = client.get(url_for("index"))
    assert b'unviewed' in res.data

    # Following the 'diff' link, it should no longer display as 'unviewed' even after we recheck it a few times
    res = client.get(url_for("diff_history_page", uuid="first"))
    assert b'Compare newest' in res.data

    time.sleep(2)

    # Do this a few times.. ensures we dont accidently set the status
    for n in range(2):
        client.get(url_for("api_watch_checknow"), follow_redirects=True)

        # Give the thread time to pick it up
        time.sleep(sleep_time_for_fetch_thread)

        # It should report nothing found (no new 'unviewed' class)
        res = client.get(url_for("index"))
        assert b'unviewed' not in res.data
        assert b'test-endpoint' in res.data

    set_original_response()

    client.get(url_for("api_watch_checknow"), follow_redirects=True)
    time.sleep(sleep_time_for_fetch_thread)
    res = client.get(url_for("index"))
    assert b'unviewed' in res.data

    # Cleanup everything
    res = client.get(url_for("api_delete", uuid="all"), follow_redirects=True)
    assert b'Deleted' in res.data


# Hard to just add more live server URLs when one test is already running (I think)
# So we add our test here (was in a different file)
def test_check_notification(client):

    set_original_response()

    # Give the endpoint time to spin up
    time.sleep(1)

    # Add our URL to the import page
    test_url = url_for('test_notification_counter', _external=True)
    res = client.post(
        url_for("import_page"),
        data={"urls": test_url},
        follow_redirects=True
    )
    assert b"1 Imported" in res.data

    # Give the thread time to pick it up
    time.sleep(3)

    # Goto the edit page, add our ignore text
    # Add our URL to the import page
    url = url_for('test_notification_endpoint', _external=True)
    notification_url = url.replace('http', 'json')
    print (">>>> Notification URL: "+notification_url)
    res = client.post(
        url_for("edit_page", uuid="first"),
        data={"notification_urls": notification_url, "url": test_url, "tag": "", "headers": ""},
        follow_redirects=True
    )
    assert b"Updated watch." in res.data

    # Give the thread time to pick it up
    time.sleep(3)

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(3)


    set_modified_response()

    # Trigger a check
    client.get(url_for("api_watch_checknow"), follow_redirects=True)

    # Give the thread time to pick it up
    time.sleep(3)

    # Check it triggered
    res = client.get(
        url_for("test_notification_counter"),
    )
    print (res.data)

    assert bytes("we hit it".encode('utf-8')) in res.data



def test_check_access_control(app, client):
    # Still doesnt work, but this is closer.
    return
    with app.test_client() as c:

        # Check we dont have any password protection enabled yet.
        res = c.get(url_for("settings_page"))
        assert b"Remove password" not in res.data

        # Enable password check.
        res = c.post(
            url_for("settings_page"),
            data={"password": "foobar"},
            follow_redirects=True
        )
        assert b"Password protection enabled." in res.data
        assert b"LOG OUT" not in res.data
        print ("SESSION:", res.session)
        # Check we hit the login

        res = c.get(url_for("settings_page"), follow_redirects=True)
        res = c.get(url_for("login"), follow_redirects=True)

        assert b"Login" in res.data

        print ("DEBUG >>>>>",res.data)
        # Menu should not be available yet
        assert b"SETTINGS" not in res.data
        assert b"BACKUP" not in res.data
        assert b"IMPORT" not in res.data



        #defaultuser@changedetection.io is actually hardcoded for now, we only use a single password
        res = c.post(
            url_for("login"),
            data={"password": "foobar", "email": "defaultuser@changedetection.io"},
            follow_redirects=True
        )

        assert b"LOG OUT" in res.data
        res = c.get(url_for("settings_page"))

        # Menu should be available now
        assert b"SETTINGS" in res.data
        assert b"BACKUP" in res.data
        assert b"IMPORT" in res.data

        assert b"LOG OUT" in res.data

        # Now remove the password so other tests function, @todo this should happen before each test automatically

        c.get(url_for("settings_page", removepassword="true"))
        c.get(url_for("import_page"))
        assert b"LOG OUT" not in res.data