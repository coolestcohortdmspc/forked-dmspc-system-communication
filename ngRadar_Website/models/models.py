from django.db import models
from enums import Stations


class ObservatoryEvent(models.Model):
    # Mapping to your payload variables
    obs_id = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    product_type = models.CharField(max_length=50)
    product_id = models.CharField(max_length=100, unique=True)
    station = models.PositiveSmallIntegerField(
            choices=Stations.choices,
            default=Stations.GBT
        )    
    creation_time = models.DateTimeField()
    event_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # This allows us to track the transmitter and receiver stations for each event
    xmit_station = models.CharField(
        max_length=100, 
        choices=Stations.choices, 
        blank=True, null=True
    )
    rcvr_station = models.CharField(
        max_length=100, 
        choices=Stations.choices, 
        blank=True, null=True
    )

    image_file = models.ImageField(upload_to='ddm_payloads/', blank=True, null=True)
    num_bytes = models.IntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)

    def __str__(self):
        return f"Obs: {self.obs_id} | {self.xmit_station_id} -> {self.rcvr_station_id}"
    

    # def also need a user login credentials table because I deleted the
    # migration with our dummy login credentials, so we def need
    # a way to store and retrieve credentials.

    # what other tables may we need?
    