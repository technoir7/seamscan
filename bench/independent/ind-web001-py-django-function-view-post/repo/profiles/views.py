from django.shortcuts import get_object_or_404, redirect, render

from .models import Profile


def edit_profile(request, username):
    profile = get_object_or_404(Profile, user__username=username)
    if request.method == "POST":
        profile.bio = request.POST.get("bio", "")
        profile.website = request.POST.get("website", "")
        profile.save()
        return redirect("profile-detail", username=username)
    return render(request, "profiles/edit.html", {"profile": profile})
