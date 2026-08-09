from rest_framework import serializers

from apps.venues.models import Venue


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "address", "capacity", "contact_person", "contact_phone", "is_active"]
