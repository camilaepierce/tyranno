from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    # path("new", views.create_event, name="create_event"),
    path("myevents", views.myevents, name="myevents"),
    path("all", views.allevents, name="allevents"),
    path("departments", views.departments_all, name="departments_all"),
    path("departments/dc", views.dep_dc, name="dep_dc"),
    path("departments/res", views.dep_res, name="dep_res"),
    path("departments/ehs", views.dep_ehs, name="dep_ehs"),
    path("departments/ad", views.dep_ad, name="dep_ad"),
    path("event/add/", views.EventCreateView.as_view(), name="event-add"),
    path("event/update/<int:pk>/", views.EventUpdateView.as_view(), name="event-update"),
    path("event/delete/<int:pk>/", views.EventDeleteView.as_view(), name="event-delete"),
    path("event/<int:pk>", views.DetailView.as_view(), name="event"),
]