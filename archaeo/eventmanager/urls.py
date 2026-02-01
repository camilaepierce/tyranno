from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("allevents", views.allevents, name="allevents"),
    path("eventapproval", views.eventapproval, name="approval"),
    path("myevents", views.myevents, name="myevents"),
    path("event/<int:event_id>", views.event, name="event")
    #might not be able to get away with /event/
]