from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import Profile


def edit_profile(request, username):
    profile = get_object_or_404(Profile, user__username=username)
    if request.method == "POST":
        profile.bio = request.POST.get("bio", "")
        profile.website = request.POST.get("website", "")
        profile.save()
        messages.success(request, "Profile updated")
        return redirect("profile", username=username)
    return render(request, "accounts/edit_profile.html", {"profile": profile})
