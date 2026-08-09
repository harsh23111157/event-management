from rest_framework import serializers

from apps.operations.models import EventStaff, EventTask, Schedule


class EventTaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField(read_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    event = serializers.StringRelatedField(read_only=True)
    event_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = EventTask
        fields = ["id", "title", "description", "event", "event_id", "assigned_to",
                  "assigned_to_id", "due_date", "priority", "status", "notes",
                  "created_at", "updated_at", "completed_at"]
        read_only_fields = ["id", "created_at", "updated_at", "completed_at"]

    def validate(self, attrs):
        due = attrs.get("due_date")
        if due:
            from django.utils import timezone
            event_id = attrs.get("event_id") or (self.instance and self.instance.event_id)
            if event_id:
                from apps.events.models import Event
                event = Event.objects.filter(pk=event_id).first()
                if event and due < event.start_date:
                    raise serializers.ValidationError({"due_date": "Due date is before the event start."})
        return attrs


class EventStaffSerializer(serializers.ModelSerializer):
    staff = serializers.StringRelatedField(read_only=True)
    staff_id = serializers.IntegerField(write_only=True, required=True)
    event = serializers.StringRelatedField(read_only=True)
    event_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = EventStaff
        fields = ["id", "event", "event_id", "staff", "staff_id", "role", "assigned_at"]
        read_only_fields = ["id", "assigned_at"]


class ScheduleSerializer(serializers.ModelSerializer):
    responsible_staff = serializers.StringRelatedField(read_only=True)
    event = serializers.StringRelatedField(read_only=True)
    event_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = Schedule
        fields = ["id", "event", "event_id", "title", "description", "start_time",
                  "end_time", "location", "responsible_staff"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs
