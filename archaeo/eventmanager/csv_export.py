import csv
from io import StringIO

from django.http import HttpResponse
from django.utils import timezone

from eventmanager.rex_config import dorm_display_name, format_event_tags_for_export

EVENT_CSV_HEADERS = [
    "ID",
    "Event Name",
    "Dorm",
    "Group",
    "Event Location",
    "Start Date and Time",
    "End Date and Time",
    "Event Description",
    "Tags",
    "Published",
]


def _format_csv_datetime(value):
    if value is None:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M:%S")


def event_csv_row(event):
    return [
        str(event.pk).zfill(4),
        event.event_name,
        dorm_display_name(event.dorm),
        event.dorm_sub,
        event.location,
        _format_csv_datetime(event.start_time),
        _format_csv_datetime(event.end_time),
        event.description,
        format_event_tags_for_export(event.tags),
        _format_csv_datetime(event.published_at),
    ]


def events_csv_response(events, filename="rex-events.csv"):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EVENT_CSV_HEADERS)
    for event in events:
        writer.writerow(event_csv_row(event))

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
