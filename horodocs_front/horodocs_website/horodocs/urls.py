from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("add", views.horodocs, name="horodocs"),
    path("verification", views.verification, name="verification"),
    path("hash", views.hash, name="hash"),
]
