from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("entrar/", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("senha/", views.password_change, name="password"),

    path("passeios/", views.experience_list, name="experiences"),
    path("passeios/novo/", views.experience_edit, name="experience_new"),
    path("passeios/<int:pk>/", views.experience_edit, name="experience_edit"),
    path("passeios/<int:pk>/excluir/", views.experience_delete, name="experience_delete"),
    path("passeios/<int:pk>/alternar/<str:field>/", views.experience_toggle, name="experience_toggle"),
    path("passeios/<int:pk>/fotos/enviar/", views.photo_upload, name="photo_upload"),
    path("passeios/<int:pk>/fotos/ordem/", views.photo_reorder, name="photo_reorder"),
    path("passeios/<int:pk>/fotos/<int:photo_pk>/<str:action>/", views.photo_action, name="photo_action"),

    path("categorias/", views.category_list, name="categories"),
    path("categorias/nova/", views.category_edit, name="category_new"),
    path("categorias/<int:pk>/", views.category_edit, name="category_edit"),
    path("categorias/<int:pk>/alternar/", views.category_toggle, name="category_toggle"),

    path("reservas/", views.booking_list, name="bookings"),
    path("reservas/<int:pk>/", views.booking_detail, name="booking_detail"),

    path("mensagens/", views.message_list, name="messages"),
    path("mensagens/<int:pk>/alternar/", views.message_toggle, name="message_toggle"),

    path("depoimentos/", views.testimonial_list, name="testimonials"),
    path("depoimentos/novo/", views.testimonial_edit, name="testimonial_new"),
    path("depoimentos/<int:pk>/", views.testimonial_edit, name="testimonial_edit"),
    path("depoimentos/<int:pk>/excluir/", views.testimonial_delete, name="testimonial_delete"),
    path("depoimentos/<int:pk>/publicar/", views.testimonial_toggle, name="testimonial_toggle"),

    path("configuracoes/", views.site_settings, name="settings"),
]
