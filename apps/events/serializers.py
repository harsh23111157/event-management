from rest_framework import serializers

from apps.events.models import Event, EventStatus
from apps.operations.models import EventTask
from apps.vendors.models import EventVendor


class EventTaskBriefSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField()

    class Meta:
        model = EventTask
        fields = ["id", "title", "status", "priority", "due_date", "assigned_to"]


class EventVendorBriefSerializer(serializers.ModelSerializer):
    vendor = serializers.StringRelatedField()

    class Meta:
        model = EventVendor
        fields = ["id", "vendor", "contract_amount", "status"]


class EventSerializer(serializers.ModelSerializer):
    manager = serializers.StringRelatedField(read_only=True)
    venue = serializers.StringRelatedField(read_only=True)
    venue_id = serializers.IntegerField(write_only=True, required=False)
    manager_id = serializers.IntegerField(write_only=True, required=False)
    tasks = EventTaskBriefSerializer(many=True, read_only=True)
    vendors = EventVendorBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ["id", "name", "description", "event_type", "start_date", "end_date",
                  "venue", "venue_id", "manager", "manager_id", "expected_attendees",
                  "budget", "status", "rejection_reason", "created_at", "updated_at",
                  "tasks", "vendors"]
        read_only_fields = ["id", "status", "rejection_reason", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_date") or (self.instance and self.instance.start_date)
        end = attrs.get("end_date") or (self.instance and self.instance.end_date)
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        budget = attrs.get("budget", self.instance and self.instance.budget)
        if budget is not None and budget <= 0:
            raise serializers.ValidationError({"budget": "Budget must be greater than zero."})
        return attrs
