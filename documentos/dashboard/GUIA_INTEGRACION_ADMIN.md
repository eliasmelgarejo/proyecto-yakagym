# Integración YakaGym Theme - Django Admin

## Resumen
Esta guía unifica el estilo del Dashboard Dark Mode con todo el Django Admin.

---

## Paso 1: Estructura de Archivos

Copia estos archivos a tu proyecto Django:

```
tu_proyecto/
├── static/
│   ├── admin/
│   │   └── css/
│   │       └── custom_admin.css      <-- Copiar archivo
│   └── images/
│       └── yakagym_logo.png          <-- Tu logo
├── templates/
│   └── admin/
│       ├── base_site.html            <-- Copiar archivo
│       └── app_list.html             <-- Copiar archivo
└── settings.py
```

---

## Paso 2: Configuración en settings.py

### 2.1 Asegurar que STATIC y TEMPLATES estén configurados:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # <-- Importante
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

### 2.2 Agregar humanize (para números formateados):

```python
INSTALLED_APPS = [
    # ... tus apps
    'django.contrib.humanize',  # <-- Agregar para filtros de números
]
```

---

## Paso 3: Configurar URLs para servir archivos estáticos (Modo Desarrollo)

En tu `urls.py` principal:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... tus urls
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## Paso 4: Configurar el Admin Sidebar (Django 3.1+)

Asegúrate de tener activada la nueva navegación lateral en `settings.py`:

```python
# Opcional pero recomendado para mejor experiencia
ADMIN_ENABLED = True
```

Y en tu `admin.py` principal (opcional, para mejorar títulos):

```python
admin.site.site_header = 'YakaGym - Administración'
admin.site.site_title = 'YakaGym'
admin.site.index_title = 'Panel de Control'
```

---

## Paso 5: Verificación

1. **Recolectar estáticos** (si estás en producción):
   ```bash
   python manage.py collectstatic
   ```

2. **Reiniciar servidor** de desarrollo:
   ```bash
   python manage.py runserver
   ```

3. **Limpiar caché** del navegador (Ctrl+Shift+R)

---

## Personalizaciones Adicionales (Opcional)

### Cambiar colores del tema

Edita `custom_admin.css` y modifica las variables CSS al inicio:

```css
:root {
    --yg-accent: #16a34a;      /* Verde principal */
    --yg-accent-blue: #1d4ed8; /* Azul secundario */
    --yg-danger: #dc2626;      /* Rojo alertas */
}
```

### Agregar más iconos

Edita `app_list.html` y añade en la sección de iconos:

```html
{% elif model_name == 'tunuevomodelo' %}<i class="fas fa-icono" style="width: 20px;"></i>
```

Lista de iconos disponibles: https://fontawesome.com/icons

### Ocultar apps del menú

Si quieres ocultar ciertos modelos del sidebar, edita tu `admin.py`:

```python
@admin.register(TuModelo)
class TuModeloAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False  # No aparece en el sidebar
```

---

## Solución de Problemas

### Problema: No se ven los estilos
**Solución**: Verificar que `STATICFILES_DIRS` incluya la carpeta static del proyecto

### Problema: No se ve el logo
**Solución**: Verificar ruta en `base_site.html`:
```html
<img src="{% static 'images/yakagym_logo.png' %}">
```
Y asegurar que el archivo existe en `static/images/`

### Problema: Los iconos no aparecen
**Solución**: Verificar conexión a internet (Font Awesome se carga desde CDN) o descargar localmente.

### Problema: El sidebar no aparece
**Solución**: Django 3.1+ requiere activación explícita. Asegúrate de no tener:
```python
admin.site.disable_action('delete_selected')  # o configuraciones que desactiven features
```

---

## Resultado Esperado

- ✅ Header oscuro con logo YakaGym
- ✅ Sidebar oscuro con iconos FontAwesome
- ✅ Botones verdes (estilo dashboard)
- ✅ Tablas con fondo oscuro y texto claro
- ✅ Formularios con estilo dark mode
- ✅ Breadcrumbs oscuros
- ✅ Mensajes de éxito/error con estilos verdes/rojos
