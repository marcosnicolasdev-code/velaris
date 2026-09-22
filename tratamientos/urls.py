from django.urls import path
from . import views

urlpatterns = [
    path("", views.tratamiento_lista, name= 'tratamiento_lista'), 
    path("crear/", views.tratamiento_crear, name='tratamiento_crear'), 
    path("<int:id_tratamiento>/editar/", views.tratamiento_editar, name='tratamiento_editar'), 
    path("<int:id_tratamiento>/eliminar/", views.tratamiento_borrar, name='tratamiento_borrar'),
   
# --------PLAN PAGO--------------
path("planes/", views.planpago_lista, name="planpago_lista"),
path("planes/nuevo/", views.planpago_crear, name="planpago_crear"),
path("planes/<str:id>/editar", views.planpago_editar, name="planpago_editar"),
path("planes/<str:id>/borrar", views.planpago_borrar, name="planpago_borrar"),


#----------Sesiones-------------
path("sesiones/", views.sesion_lista, name="sesion_lista"),
path("sesiones/nuevo/", views.sesion_crear, name="sesion_crear"),
path("sesiones/<int:id_sesion>/editar", views.sesion_editar, name="sesion_editar"),
path("sesiones/<int:id_sesion>/borrar", views.sesion_borrar, name="sesion_borrar"),

]
