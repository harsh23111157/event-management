from rest_framework import serializers

from apps.vendors.models import EventVendor, Vendor


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "name", "service_type", "contact_person", "email", "phone", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class EventVendorSerializer(serializers.ModelSerializer):
    vendor = serializers.StringRelatedField(read_only=True)
    vendor_id = serializers.IntegerField(write_only=True, required=True)
    event = serializers.StringRelatedField(read_only=True)
    event_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = EventVendor
        fields = ["id", "event", "event_id", "vendor", "vendor_id", "contract_amount",
                  "service_description", "status", "created_at"]
        read_only_fields = ["id", "created_at"]
