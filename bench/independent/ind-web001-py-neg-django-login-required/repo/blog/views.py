from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import PostForm


@login_required
def new_post(request):
    form = PostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("post-detail", pk=post.pk)
    return render(request, "blog/new.html", {"form": form})
