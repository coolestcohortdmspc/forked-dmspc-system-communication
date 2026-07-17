from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

#libraries used for data streaming
import json
from django.http import StreamingHttpResponse, JsonResponse

# s3 imports
import boto3
from botocore.config import Config

#libraries used for lock status
from django.core.cache import cache

from ngRadar_Website.enums import Stations
from ngRadar_Website.models.models import ObservatoryEvent, uiEvent, ngrok_endpoint
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.db.models import Avg
from confluent_kafka import Producer
import os 
import uuid
from datetime import datetime, timezone 
from dotenv import load_dotenv


load_dotenv(override=True)

#program constants
DATE_TIME_STRING=19


def get_obs_events():
    """Helper function to keep data uniform across view updates"""

    latest_events = ObservatoryEvent.objects.order_by("-event_time")
    ui_event = uiEvent.objects.order_by("-event_time")
    # Calculate the average latency of the last 20 records
    latest_20 = latest_events[:20]
    avg_latency = latest_20.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
    current_waveform = ui_event.first().selected_waveform if ui_event.exists() else None

    return {
        'latest_events': latest_events,
        'latest_event': latest_events.first() if latest_events else None,
        'ui_event': ui_event.first() if ui_event else None,
        'gbt_event': latest_events.filter(station=Stations.GBT).order_by('-event_time').first(), # only care about the latest event for home gbt partial
        'dsoc_event': latest_events.filter(station=Stations.DSOC).order_by('-event_time').first(), # only care about the latest event for home dsoc partial
        'avg_latency': round(avg_latency, 2),
        'current_waveform': current_waveform
    }



# Keep as a placeholder when we develop this feature.
# def create_observation(request):
#     # this is the initial view to load the newObservation page
#     return render(request, 'ngRadar_Website/newObservation.html')

def get_Message_Latency():
    last_message_latency_str = str(ObservatoryEvent.objects.last().latency_ms)
    last_message_time_str = str(ObservatoryEvent.objects.last().event_time)
    last_message_time_str = last_message_time_str[:DATE_TIME_STRING]  # Truncate to first 20 characters
    
    data_to_send = {
        "latency": last_message_latency_str,
        "time_sent": last_message_time_str
    }
    yield f"data: {json.dumps(data_to_send)}\n\n"


def latency_graphing(request):
    response = StreamingHttpResponse(
        get_Message_Latency(),
        content_type="text/event-stream; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache"
    return response


def serve_image(request, uuid):
    event = get_object_or_404(ObservatoryEvent, uuid=uuid)

    # Configure boto3 to use the internal domain for API calls,
    # but generate presigned URLs using the public domain.
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["WEED_S3_INTERNAL_DOMAIN"], 
        aws_access_key_id=os.environ["WEED_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["WEED_S3_SECRET_KEY"],
        config=Config(s3={'addressing_style': 'path'}) # Keeps bucket in the path layout
    )

    # Ask seaweedfs to generate a direct, temporary link to the file
    # This happens instantly without loading any image bytes into Django memory
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': os.environ["WEED_S3_BUCKET"], 
            'Key': event.image_key
        },
        ExpiresIn=3600 # The link is valid for 1 hour (3600 seconds)
    )
    
      # Swap out the internal network name for the public domain before redirecting
      # Will make the user's browser go fetch the image directly from seaweedfs using this URL
      # Each time this view is called (i.e. on page load, refresh, etc.) a new 1 hour url is created.
      # Better security this way
    public_url = presigned_url.replace(
        os.environ["WEED_S3_INTERNAL_DOMAIN"], 
        os.environ["WEED_S3_PUBLIC_DOMAIN"]
    )
    
    return redirect(public_url)




# Function for lock down user
# Return True if event time is greater than lock time 
# Othere wise False  
def lock_status(request):
    lock_time = cache.get('submit_locked', None)
    if lock_time is None:
        return JsonResponse({"locked": False})
    elif ObservatoryEvent.objects.filter(event_time__gt=lock_time, image_key__isnull=False):
        cache.delete('submit_locked')
        return JsonResponse({'locked':False})
    return JsonResponse({'locked':True})

# Need a function AND another partial template for handling the user inputted payload
def submit_waveform(request):
    if request.method == "POST":
        uuid_input = uuid.uuid4()
        waveform  = request.POST.get('waveform')
        timestamp = datetime.now(timezone.utc)
        # Database version
        ui_Event = uiEvent.objects.create(
            uuid = uuid_input,
            selected_waveform = waveform,
            event_time = timestamp
        )

        # p = Path("../../../out/ngrok_endpoint.env")
        # text = p.read_text().strip()

        # bootstrap = None
        # for line in text.splitlines():
        #     if line.startswith("BOOTSTRAP_SERVER="):
        #         bootstrap = line.split("=", 1)[1].strip()
        #         break

        # if not bootstrap:
        #     raise RuntimeError("BOOTSTRAP_SERVER not found in /out/ngrok_endpoint.env")
        
        bootstrap = ngrok_endpoint.objects.last().bootstrap

        # Kafka version 
        topic = "user_input"
        config = {
            "bootstrap.servers": bootstrap,
            "message.max.bytes": 8388608,
            "client.id": "ui-producer"}
        message = "User input a new waveform."

        def produce(topic, config, key, value):
            producer = Producer(config)
            producer.produce(topic, key=key, value=value)
            
            producer.flush()

        def main():
            key = uuid_input.hex  # Use the UUID as the key for the Kafka message
            value = json.dumps(message).encode("utf-8")
            produce(topic, config, key, value)
        main()
        
        # add a cache for submit time
        cache.set('submit_locked', datetime.now(timezone.utc))
    return redirect('home')


#====================================================
# Render the templates
#====================================================


@cache_control(no_cache=True, must_revalidate=True, no_store=True) #Desmond's Auth token fix - comment if we decide not to use
def login_view(request):
    if request.method == 'POST':
        username_input = request.POST['username']
        password_input = request.POST['password']
        
        # This automatically uses the Argon2 settings to verify the password string
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'registration/login.html')
        
    # Tung's auth token fix - uncomment if we decide to use this
    # response = render(request, 'registration/login.html')
    # response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

    return render(request, 'registration/login.html')


@login_required
def home_view(request):
    return render(
        request,
        "ngRadar_Website/home.html",
        get_obs_events(),
    )


@login_required
def dashboard_view(request):
    return render(
        request,
        "ngRadar_Website/dashboard.html",
        get_obs_events(),
    )


def event_table_partial(request):
    # this is the partial template view for updating the observatory events table
    return render(
        request,
        "ngRadar_Website/partials/dashboard_updates.html",
        get_obs_events(),
    )

def status_partial(request):
    # this is the partial template view for the status box on the home page

    return render(
        request,
        "ngRadar_Website/partials/status_partial.html",
        get_obs_events(),
    )


def dsoc_event_partial(request):
    # this is the partial template view for latest dsoc event image on home page

    return render(
        request,
        "ngRadar_Website/partials/dsoc_home_partial.html",
        get_obs_events(),
    )


def gbt_event_partial(request):
    # this is the partial template view for latest gbt event data on home page
    return render(
        request,
        "ngRadar_Website/partials/gbt_home_partial.html",
        get_obs_events(),
    )

