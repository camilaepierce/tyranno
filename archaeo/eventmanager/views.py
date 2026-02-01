from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

from .models import RexEvent

def index(request):
    upcoming_events = RexEvent.objects.order_by("-start_time")[:5]
    template = loader.get_template("eventmanager/index.html")
    context = {"upcoming_events_list": upcoming_events}
    return HttpResponse(template.render(context, request))

def myevents(request):
    return HttpResponse("My Events page")

def allevents(request):
    return HttpResponse("All events view")

def createevent(request):
    return HttpResponse("Create a new event here")

def eventapproval(request):
    return HttpResponse("Approve events here")

def event(request, event_id):
    return HttpResponse("Inspecting event %s." % event_id)