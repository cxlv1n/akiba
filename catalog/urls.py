from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.car_list, name="list"),
    path("<int:car_id>/", views.car_detail, name="detail"),
]



