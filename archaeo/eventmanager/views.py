from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.template import loader
from django.views import generic

from .models import RexEvent, RexUser
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from .forms import EventForm


def get_user_context(request):
    """Get user role and context information"""
    user_role = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Try to get role from RexUser model
        try:
            rex_user = RexUser.objects.get(username=request.user.username)
            user_role = rex_user.role
        except RexUser.DoesNotExist:
            pass
    
    approver_roles = ['DormCon', 'AD', 'RES', 'EHS']
    admin_roles = ['DormCon', 'AD']
    
    return {
        'user_role': user_role,
        'approver_roles': approver_roles,
        'admin_roles': admin_roles,
    }


class EventCreateView(CreateView):
    model = RexEvent
    form_class = EventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        return context


class EventUpdateView(UpdateView):
    model = RexEvent
    form_class = EventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        return context


class EventDeleteView(DeleteView):
    model = RexEvent
    success_url = reverse_lazy("index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        return context


class IndexView(generic.ListView):
    template_name = "eventmanager/index.html"
    context_object_name = "upcoming_events_list"
    
    def get_queryset(self):
        """Return the last five published questions."""
        return RexEvent.objects.order_by("-start_time")[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        return context


class DetailView(generic.DetailView):
    model = RexEvent
    template_name = "eventmanager/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        return context


def myevents(request):
    upcoming_events = RexEvent.objects.order_by("-start_time")
    template = loader.get_template("eventmanager/myevents.html")
    context = {
        "upcoming_events_list": upcoming_events
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def allevents(request):
    upcoming_events = RexEvent.objects.order_by("-start_time")
    template = loader.get_template("eventmanager/allevents.html")
    context = {
        "upcoming_events_list": upcoming_events
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def departments_all(request):
    upcoming_events = RexEvent.objects.order_by("-start_time")
    template = loader.get_template("departments/all.html")
    context = {
        "upcoming_events_list": upcoming_events
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def dep_dc(request):
    upcoming_events = RexEvent.objects.filter(dc_status__in=['PE', 'FL']).order_by("-start_time")
    template = loader.get_template("departments/dc/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "DormCon"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def dep_res(request):
    upcoming_events = RexEvent.objects.filter(res_status__in=['PE', 'FL']).order_by("-start_time")
    template = loader.get_template("departments/res/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "RES"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def dep_ehs(request):
    upcoming_events = RexEvent.objects.filter(ehs_status__in=['PE', 'FL']).order_by("-start_time")
    template = loader.get_template("departments/ehs/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "EHS"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def dep_ad(request):
    upcoming_events = RexEvent.objects.filter(ad_status__in=['PE', 'FL']).order_by("-start_time")
    template = loader.get_template("departments/ad/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "AD"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


def create_event(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            return redirect('event', pk=event.pk)
    else:
        form = EventForm()
    
    template = loader.get_template("eventmanager/create_event.html")
    context = {"form": form}
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))
