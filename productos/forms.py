from django import forms    
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "codigo_producto", "nombre_producto", "cantidad_producto", 
            "categoria_producto", "precio_producto", "stock_minimo",       
        ]