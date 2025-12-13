from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("process/", views.process, name="process"),
    path("contacts/", views.contacts, name="contacts"),
]



