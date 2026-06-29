from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.template import loader
from django.views import generic
import json

from .models import RexEvent, RexUser, SiteConfiguration
from .csv_export import events_csv_response
from .rex_config import dorm_groups_for_js
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from .forms import EventForm, ApprovalForm


def _user_is_admin(user_context):
    return user_context.get("user_role") in user_context.get("admin_roles", [])


def _admin_required_response(request):
    user_context = get_user_context(request)
    if _user_is_admin(user_context):
        return None
    return HttpResponseForbidden("You do not have permission to access this page.")


def get_user_context(request):
    """Get user role and context information"""
    rex_user = _get_rex_user(request)
    user_role = rex_user.role if rex_user else None

    approver_roles = ['DormCon', 'AD', 'RES', 'EHS']
    admin_roles = ['DormCon', 'AD', 'RES', 'EHS']
    site_config = SiteConfiguration.load()

    return {
        'user_role': user_role,
        'rex_user': rex_user,
        'approver_roles': approver_roles,
        'admin_roles': admin_roles,
        'event_editing_enabled': site_config.allow_event_editing,
    }


def _get_rex_user(request):
    if hasattr(request, "user"):
        return RexUser.for_auth_user(request.user)
    return None


def _add_approval_context(context, event, user_role):
    if not user_role or not event.role_can_approve(user_role):
        return

    status_field, comment_field = RexEvent.ROLE_TO_APPROVAL[user_role]
    context['approval_form'] = ApprovalForm()
    context['can_approve'] = True
    context['approval_status_field'] = status_field
    context['approval_comment'] = getattr(event, comment_field)


def _user_can_edit_event(rex_user, event, editing_enabled):
    return (
        editing_enabled
        and rex_user is not None
        and event.created_by_id == rex_user.pk
    )


DELETE_CONFIRMATION_PHRASE = (
    "tell camila to update this message before deployment"
)


def _add_edit_context(context, event, rex_user, editing_enabled):
    context['can_edit_event'] = _user_can_edit_event(rex_user, event, editing_enabled)


def _event_form_context():
    return {
        "dorm_groups_json": json.dumps(dorm_groups_for_js()),
    }


class EventEditPermissionMixin:
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        rex_user = _get_rex_user(request)
        site_config = SiteConfiguration.load()
        if not _user_can_edit_event(rex_user, self.object, site_config.allow_event_editing):
            return HttpResponseForbidden("You do not have permission to modify this event.")
        return super().dispatch(request, *args, **kwargs)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = RexEvent
    form_class = EventForm
    template_name = "eventmanager/create_event.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        context.update(_event_form_context())
        return context

    def form_valid(self, form):
        rex_user = _get_rex_user(self.request)
        if rex_user:
            form.instance.created_by = rex_user
        return super().form_valid(form)


class EventUpdateView(EventEditPermissionMixin, LoginRequiredMixin, UpdateView):
    model = RexEvent
    form_class = EventForm
    template_name = "eventmanager/create_event.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        context.update(_event_form_context())
        return context


class EventDeleteView(EventEditPermissionMixin, LoginRequiredMixin, DeleteView):
    model = RexEvent
    template_name = "eventmanager/confirm_delete.html"
    success_url = reverse_lazy("myevents")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_context(self.request))
        context["delete_confirmation_phrase"] = DELETE_CONFIRMATION_PHRASE
        return context

    def post(self, request, *args, **kwargs):
        confirmation = request.POST.get("confirmation_phrase", "").strip()
        if confirmation != DELETE_CONFIRMATION_PHRASE:
            messages.error(
                request,
                "Deletion cancelled. Type the exact confirmation message to proceed.",
            )
            return self.render_to_response(self.get_context_data())
        return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        event_name = self.object.event_name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'"{event_name}" has been deleted.')
        return response


def logged_out(request):
    if request.user.is_authenticated:
        return redirect("index")

    context = get_user_context(request)
    return render(request, "eventmanager/logged_out.html", context)


class IndexView(generic.ListView):
    template_name = "eventmanager/index.html"
    context_object_name = "upcoming_events_list"
    
    def get_queryset(self):
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
        _add_approval_context(context, self.object, context.get('user_role'))
        _add_edit_context(
            context,
            self.object,
            context.get('rex_user'),
            context.get('event_editing_enabled', True),
        )
        return context


@login_required
def approve_event(request, pk):
    event = get_object_or_404(RexEvent, pk=pk)
    user_context = get_user_context(request)
    user_role = user_context.get('user_role')
    approval_mapping = RexEvent.ROLE_TO_APPROVAL.get(user_role)

    if not approval_mapping or not event.role_can_approve(user_role):
        return HttpResponseForbidden("You do not have permission to approve this event.")

    status_field, comment_field = approval_mapping

    if request.method != 'POST':
        return redirect('event', pk=pk)

    form = ApprovalForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the errors in your approval submission.")
        return redirect('event', pk=pk)

    setattr(event, status_field, form.cleaned_data['status'])
    setattr(event, comment_field, form.cleaned_data['comment'])
    event.save()

    messages.success(request, f"Approval updated for {event.event_name}.")
    return redirect(_approval_redirect_name(user_role))


def _approval_redirect_name(user_role):
    return {
        'DormCon': 'dep_dc',
        'AD': 'dep_ad',
        'RES': 'dep_res',
        'EHS': 'dep_ehs',
    }.get(user_role, 'index')


@login_required
def myevents(request):
    rex_user = _get_rex_user(request)
    user_context = get_user_context(request)
    upcoming_events = RexEvent.objects.order_by("-start_time")
    if rex_user:
        upcoming_events = upcoming_events.filter(created_by=rex_user)
    template = loader.get_template("eventmanager/myevents.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "can_edit_event": user_context.get("event_editing_enabled", True),
    }
    context.update(user_context)
    return HttpResponse(template.render(context, request))


@login_required
def allevents(request):
    forbidden = _admin_required_response(request)
    if forbidden:
        return forbidden

    upcoming_events = RexEvent.objects.order_by("-start_time")
    template = loader.get_template("eventmanager/allevents.html")
    context = {
        "upcoming_events_list": upcoming_events
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


@login_required
def allevents_csv(request):
    forbidden = _admin_required_response(request)
    if forbidden:
        return forbidden

    events = RexEvent.objects.order_by("-start_time")
    return events_csv_response(events)


@login_required
def departments_all(request):
    upcoming_events = RexEvent.objects.order_by("-start_time")
    template = loader.get_template("departments/all.html")
    context = {
        "upcoming_events_list": upcoming_events
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


@login_required
def dep_dc(request):
    upcoming_events = RexEvent.objects.filter(dc_status__in=['PE', 'FL']).order_by("-start_time")
    template = loader.get_template("departments/dc/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "DormCon"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


@login_required
def dep_res(request):
    upcoming_events = RexEvent.objects.filter(
        dc_status='AP',
        res_status__in=['PE', 'FL'],
    ).order_by("-start_time")
    template = loader.get_template("departments/res/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "RES"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


@login_required
def dep_ehs(request):
    upcoming_events = RexEvent.objects.filter(
        dc_status='AP',
        ehs_status__in=['PE', 'FL'],
    ).order_by("-start_time")
    template = loader.get_template("departments/ehs/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "EHS"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))


@login_required
def dep_ad(request):
    upcoming_events = RexEvent.objects.filter(
        dc_status='AP',
        ad_status__in=['PE', 'FL'],
    ).order_by("-start_time")
    template = loader.get_template("departments/ad/pending.html")
    context = {
        "upcoming_events_list": upcoming_events,
        "department": "AD"
    }
    context.update(get_user_context(request))
    return HttpResponse(template.render(context, request))
