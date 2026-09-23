from pathlib import Path
from unittest.mock import patch, MagicMock

from ngRadar_Website.enums import Stations, Message, Status
from datetime import datetime, timezone
from ngRadar_Website.models.models import ObservatoryEvent
from django.test import RequestFactory
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import call

import json
import uuid


# ==============================================================================
# IMPORTANT:
# Because we read "ngrok_endpoint.env" on import, we need to patch the Path globally
# before importing all the functions we want to test.
# ==============================================================================
mock_env_data = "BOOTSTRAP_SERVER=localhost:9092\nSOME_OTHER_VAR=value" 
with patch("pathlib.Path.read_text", return_value=mock_env_data):
    from ngRadar_Website.views.views import (
        serve_image,
        lock_status,
        submit_waveform,
        login_view,
        logout_view,
        home_view,
        dashboard_view,
        event_table_partial,
        RECORDS_TO_DISPLAY,
        get_latest_image_events,
        get_dashboard_context,
        latency_data,
    )

# ==============================================================================
# 2. serve_image Test
# ==============================================================================

@patch.dict(
    "os.environ",
    {
        "WEED_S3_BUCKET": "fake_bucket"
    },
)
@patch("ngRadar_Website.views.views.get_object_or_404")
@patch("ngRadar_Website.views.views.create_presigned_url")
@patch("ngRadar_Website.views.views.redirect")
def test_serve_image(mock_redirect, mock_presigned, mock_get_obj):
    """Scenario 1: no errors"""

    mock_event = MagicMock()
    mock_event.image_key = "images/test.png"
    mock_get_obj.return_value = mock_event

    mock_url = MagicMock()
    mock_presigned.return_value = mock_url

    mock_redirect.return_value = "output"

    #call the function:
    result = serve_image(
            request="request",
            uuid="uuid",
        )

    mock_get_obj.assert_called_once_with(ObservatoryEvent, uuid="uuid")
    mock_presigned.assert_called_once_with(mock_event)
    assert result == "output"
    mock_redirect.assert_called_once_with(mock_url)

@patch.dict(
    "os.environ",
    {
        "WEED_S3_BUCKET": "fake_bucket"
    },
)
@patch("ngRadar_Website.views.views.get_object_or_404")
@patch("ngRadar_Website.views.views.create_presigned_url")
def test_serve_image_error(mock_presigned, mock_get_obj, caplog):
    """Scenario 2: exception raised"""

    mock_event = MagicMock()
    mock_event.image_key = "images/test.png"
    mock_get_obj.return_value = mock_event

    mock_presigned.side_effect = Exception("Failed to connect.")

    #call the function:
    serve_image(request = "request", uuid = "uuid")

    mock_get_obj.assert_called_once_with(ObservatoryEvent, uuid="uuid")
    mock_presigned.assert_called_once_with(mock_event)
    assert "Failed to retrieve image from SeaweedFS." in caplog.text

# ===============================================================================
# 3. Submit waveform test
# ===============================================================================

@patch("ngRadar_Website.views.views.datetime")
@patch("ngRadar_Website.views.views.cache")
@patch("ngRadar_Website.views.views.write_transfer_progress")
@patch("ngRadar_Website.views.views.bootstrap")
@patch("ngRadar_Website.views.views.send_kafka_message")
def test_submit_waveform(mock_kafka, mock_bootstrap, Mock_ProgressBar, Mock_Cache, mock_datetime):
    #create simulated data
    mock_uuid = uuid.UUID('12345678-1234-5678-1234-567812345678')
    test_timestamp = datetime(2026, 8, 17, 12, 30, 45, tzinfo=timezone.utc)
    test_waveform = '45'

    #create fixed return value for date time
    mock_datetime.now.return_value=test_timestamp

    #generate a mock post request
    factory = RequestFactory()
    myRequest = factory.post('home/submit-waveform/', data={'waveform':test_waveform})
    myRequest.user = User(username="testuser")

    #mock a UI Event
    Mock_EVENT = MagicMock()
    Mock_EVENT.uuid = mock_uuid
    Mock_EVENT.selected_waveform = test_waveform
    Mock_EVENT.event_time = test_timestamp

    mock_bootstrap.return_value = (
        "test_topic",
        "test_config",
    )

    data = submit_waveform(myRequest)
    
    # Assert cache was set
    Mock_Cache.set.assert_called_once()
    #assert call to reset progress bar was made
    Mock_ProgressBar.assert_called_once()
    mock_kafka.assert_called_once_with(
        message_type=Message.UI_EVENT,
        producer_topic="test_topic",
        producer_config="test_config",
        waveform_requester="testuser",
        station=Stations.UI,
        tx_waveform=test_waveform,
        rec_waveform=test_waveform,
        message=f"testuser submitted waveform {test_waveform}.",
    )
    mock_bootstrap.assert_called_once_with(Stations.UI)

# ==============================================================================
# 4. login_view Test
# ==============================================================================


@patch("ngRadar_Website.views.views.redirect")
def test_login_view_auth(mock_redirect):
    """Scenario 1: user is authenticated"""

    #We need this django function to generate a fake http request for us:
    factory = RequestFactory()
    request = factory.get("/login/")

    request.user = MagicMock()
    request.user.is_authenticated = True

    # Make redirect() return a real response object Django can set headers on
    expected_url = reverse("home")  # adjust if different
    mock_redirect.return_value = HttpResponseRedirect(expected_url)

    response = login_view(request)

    mock_redirect.assert_called_once_with("home")
    assert response.status_code == 302
    assert response.url == expected_url

@patch("ngRadar_Website.views.views.authenticate")
@patch("ngRadar_Website.views.views.login")
@patch("ngRadar_Website.views.views.redirect")
@patch("ngRadar_Website.views.views.logout_view")
def test_login_view_post_valid(mock_logout, mock_redirect, mock_login, mock_auth):
    """Scenario 2: method = POST with valid credentials"""

    factory = RequestFactory()
    request = factory.post("/login/", {
        "username": "name",
        "password": "secret"
    })

    #set auth to False to avoid first if statement:
    request.user = MagicMock()
    request.user.is_authenticated = False

    mock_user = MagicMock()
    mock_auth.return_value = mock_user

    mock_response = HttpResponseRedirect("/home/")
    mock_redirect.return_value = mock_response

    output = login_view(request)

    mock_login.assert_called_once_with(request, mock_user)
    assert output == mock_response
    mock_auth.assert_called_once_with(request, username="name", password="secret")
    mock_logout.assert_not_called()

@patch("ngRadar_Website.views.views.authenticate")
@patch("ngRadar_Website.views.views.render")
@patch("ngRadar_Website.views.views.messages.error")
@patch("ngRadar_Website.views.views.logout_view")
def test_login_view_post_invalid(mock_logout, mock_msg_error, mock_render, mock_auth):
    """Scenario 3: method = POST with IN-valid credentials"""

    factory = RequestFactory()
    request = factory.post("/login/", {
        "username": "name",
        "password": "secret"
    })

    #set auth to False to avoid first if statement:
    request.user = MagicMock()
    request.user.is_authenticated = False

    mock_user = None
    mock_auth.return_value = mock_user

    mock_response = HttpResponse("login page")
    mock_render.return_value = mock_response

    output = login_view(request)

    assert output == mock_response
    mock_auth.assert_called_once_with(request, username="name", password="secret")
    mock_msg_error.assert_called_once_with(request, "Invalid username or password.")
    mock_render.assert_called_once_with(request, 'registration/login.html')
    mock_logout.assert_not_called()


# ==============================================================================
# 6. lock_status Test
# ==============================================================================

@patch("ngRadar_Website.views.views.cache.get")
@patch("ngRadar_Website.views.views.JsonResponse")
def test_lock_status_none(mock_json, mock_cache_get):
    """Scenario 1: lock time is None"""

    mock_cache_get.return_value = None
    mock_json.return_value = "fake_json_response"

    request = RequestFactory().get("/lock-status/")
    output = lock_status(request)

    assert output == "fake_json_response"
    mock_cache_get.assert_called_once_with('submit_locked')
    mock_json.assert_called_once_with({"locked": False,
                                 "error": False})


@patch("ngRadar_Website.views.views.cache.delete")
@patch("ngRadar_Website.views.views.cache.get")
@patch("ngRadar_Website.views.views.JsonResponse")
@patch("ngRadar_Website.views.views.ObservatoryEvent")
def test_lock_matching_event_time(mock_ObservatoryEvent, mock_json, mock_cache_get, mock_cache_delete):
    """Scenario 2: lock time matches the event time"""

    mock_cache_get.return_value = "fake_time"
    mock_json.return_value = "fake_json_response"

    mock_ObservatoryEvent.objects.return_value.filter.return_value = True

    request = RequestFactory().get("/lock-status/")
    output = lock_status(request)

    assert output == "fake_json_response"
    mock_cache_get.assert_called_once_with('submit_locked')
    mock_json.assert_called_once_with({"locked": False,
                                 "error": False})
    mock_cache_delete.assert_called_once_with('submit_locked')


@patch("ngRadar_Website.views.views.cache.get")
@patch("ngRadar_Website.views.views.JsonResponse")
def test_lock_status_exception(mock_json, mock_cache_get):
    """Scenario 3: Exception is raised"""

    mock_cache_get.side_effect = Exception("Caching Error")

    mock_json.return_value = "fake_json_response"

    request = RequestFactory().get("/lock-status/")
    output = lock_status(request)

    assert output == "fake_json_response"
    mock_cache_get.assert_called_once_with('submit_locked')
    mock_json.assert_called_once_with({
                                "locked": True,
                                "error": True,
                                "message": "Unable to determine lock status."
                            }, status=503)

# ==============================================================================
# 7. logout_view Test
# ==============================================================================
@patch("ngRadar_Website.views.views.redirect")
@patch("ngRadar_Website.views.views.logout")
def test_logout_view(mock_logout, mock_redirect):
    #We need this django function to generate a fake http request for us:
    factory = RequestFactory()
    request = factory.post("/logout/")

    logout_view(request)

    mock_logout.assert_called_once_with(request)
    mock_redirect.assert_called_once_with("login")


# ==============================================================================
# 8. home_view Test
# ==============================================================================

@patch("ngRadar_Website.views.views.render")
@patch("ngRadar_Website.views.views.get_home_context")
def test_home_view(mock_get_home_context, mock_render):
    request = MagicMock()

    response = HttpResponse("fake_response")
    mock_render.return_value = response

    output = home_view(request)

    assert output == response
    mock_render.assert_called_once_with(request, "ngRadar_Website/home.html", mock_get_home_context())


# ==============================================================================
# 9. dashboard_view Test
# ==============================================================================

@patch("ngRadar_Website.views.views.render")
@patch("ngRadar_Website.views.views.get_dashboard_context")
def test_dashboard_view(mock_get_dashboard_context, mock_render):
    request = MagicMock()

    response = HttpResponse("fake_response")
    mock_render.return_value = response

    output = dashboard_view(request)

    assert output == response
    mock_render.assert_called_once_with(request, "ngRadar_Website/dashboard.html", mock_get_dashboard_context())


# ==============================================================================
# 10. event_table_partial Test
# ==============================================================================

@patch("ngRadar_Website.views.views.render")
@patch("ngRadar_Website.views.views.get_dashboard_context")
def test_event_table_partial(mock_get_dashboard_context, mock_render):

    response = HttpResponse("fake_response")
    mock_render.return_value = response

    request = RequestFactory().get("/lock-status/")

    # Add session to the RequestFactory request
    middleware = SessionMiddleware(lambda request: None)
    middleware.process_request(request)

    output = event_table_partial(request)

    assert output == response
    mock_render.assert_called_once_with(request, "ngRadar_Website/partials/dashboard_updates.html", mock_get_dashboard_context.return_value)

# ==============================================================================
# 11. get_latest_image_events Test
# ==============================================================================

@patch("ngRadar_Website.views.views.ObservatoryEvent")
def test_get_latest_image_events(mock_ObservatoryEvent):
    mock_ObservatoryEvent.objects.filter.return_value.exclude.return_value.exclude.return_value.order_by.return_value.first.return_value = "event"

    result = get_latest_image_events()

    assert len(result) == 10
    assert result == ["event"] * 10

# ==============================================================================
# 12. get_dashboard_context Test
# ==============================================================================

@patch("ngRadar_Website.views.views.ObservatoryEvent")
@patch("ngRadar_Website.views.views.get_current_waveform")
@patch("ngRadar_Website.views.views.get_latest_image_event")
def test_get_dashboard_context(mock_latest_image, mock_current_wf, mock_ObservatoryEvent):
    """Scenario 1: message_number is None"""

    message_number = None

    # latest_events
    latest_event = MagicMock()
    latest_event.transfer_uuid = "transfer-123"
    
    latest_events = [latest_event, MagicMock()]
    mock_ObservatoryEvent.objects.order_by.return_value.__getitem__.return_value = (
        latest_events
    )
    # avg latency
    mock_ObservatoryEvent.objects.exclude.return_value.aggregate.return_value = {
        "avg": 25.5
    }
    # transfer events
    transfer_events = ["transfer1", "transfer2"]
    mock_ObservatoryEvent.objects.filter.return_value.order_by.return_value = (
        transfer_events
    )
    # transferring count
    mock_ObservatoryEvent.objects.filter.return_value.count.return_value = 2

    result = get_dashboard_context(message_number)

    assert result == {
                    "latest_events": latest_events,
                    "latest_event": latest_event,
                    "avg_latency": round(25.5, 2),
                    "current_waveform": mock_current_wf(),
                    "latest_image_event": mock_latest_image(),
                    "transfer_events": transfer_events,
                    "transfer_resumed": True,
                }

# ==============================================================================
# 13. latency_data Test
# ==============================================================================

@patch("ngRadar_Website.views.views.ObservatoryEvent")
def test_latency_data(mock_ObservatoryEvent):

    factory = RequestFactory()
    request = factory.get("/login/")
    # Add session to the RequestFactory request
    middleware = SessionMiddleware(lambda request: None)
    middleware.process_request(request)

    events = []
    for _ in range(RECORDS_TO_DISPLAY):
        event = MagicMock()
        event.station = None
        event.status = None
        event.latency_ms = 10.123
        event.event_time = datetime.now()
        event.object_id = None
        event.target = None
        events.append(event)
    mock_ObservatoryEvent.objects.exclude.return_value.order_by.return_value.__getitem__.return_value = events

    result = latency_data(request)
    data = json.loads(result.content)

    assert len(data["latency_array"]) == RECORDS_TO_DISPLAY
