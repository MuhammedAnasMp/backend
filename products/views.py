from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Product
from .serializers import ProductSerializer
from .utils import extract_instagram_id

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for full CRUD operations on Products.
    Enforces multi-tenant isolation (sellers only manage their own items).
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return products belonging to the currently authenticated seller
        return Product.objects.filter(seller=self.request.user).order_by('-created_at')


class ResolveProductView(APIView):
    """
    Given an Instagram URL, returns the linked active product details.
    """
    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response({"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        shortcode = extract_instagram_id(url)
        if not shortcode:
            return Response({"error": "Invalid Instagram URL"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Look up active products by Instagram source_id (shortcode)
            product = Product.objects.get(source_id=shortcode, status='ACTIVE')
            return Response({
                "found": True,
                "product": {
                    "id": product.id,
                    "title": product.title,
                    "price": str(product.price) if product.price else None,
                    "is_negotiable": product.is_negotiable,
                    "media_url": product.main_media_url,
                    "seller": product.seller.username
                }
            })
        except Product.DoesNotExist:
            return Response({
                "found": False,
                "message": "Product not registered for this content",
                "shortcode": shortcode
            }, status=status.HTTP_404_NOT_FOUND)


class RegisterProductMappingView(APIView):
    """
    Registers a new product or converts an existing social source into an active product.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get("title")
        price = request.data.get("price")
        instagram_url = request.data.get("instagram_url")
        is_negotiable = request.data.get("is_negotiable", True)
        media_url = request.data.get("media_url", "")

        if not all([title, price, instagram_url]):
            return Response({"error": "Title, price, and instagram_url are required"}, status=status.HTTP_400_BAD_REQUEST)

        shortcode = extract_instagram_id(instagram_url)
        if not shortcode:
            return Response({"error": "Invalid Instagram URL"}, status=status.HTTP_400_BAD_REQUEST)

        # Create or Update Product with Status 'ACTIVE' (Published)
        product, created = Product.objects.update_or_create(
            source_id=shortcode,
            defaults={
                "seller": request.user,
                "title": title,
                "price": price,
                "is_negotiable": is_negotiable,
                "main_media_url": media_url,
                "source_type": "REEL",
                "status": "ACTIVE"
            }
        )

        return Response({
            "message": "Product registered and mapped successfully",
            "product_id": product.id,
            "shortcode": shortcode,
            "created": created
        }, status=status.HTTP_201_CREATED)
