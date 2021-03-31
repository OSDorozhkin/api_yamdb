
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticatedOrReadOnly,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets, filters

from .models import Categories, Genres, Titles, Reviews
from .filters import ModelFilterTitles
from .permissions import GeneralPermission, IsAdmin, IsAuthorModerAdmin
from .serializers import (
    CategoriesSerializer,
    TitlesReadSerializer,
    TitlesWriteSerializer,
    GenresSerializer,
    UserSerializer,
    CommentsSerializer,
    ReviewsSerializers,
    ConfirmationCodeSerializer,
)


User = get_user_model()


@csrf_exempt
def emailConfirmation(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email is None:
            return HttpResponse("Мыло не получено")

        user = get_object_or_404(User, email=email)
        confirmation_code = default_token_generator.make_token(user)
        send_mail(
            subject='email_confirmation',
            message=confirmation_code,
            from_email='yamdb@ya.ru',
            recipient_list=[email, ]
        )
        return HttpResponse('Confirmation code was sent to your email:')


@api_view(['POST'])
@permission_classes([AllowAny])
def SendToken(request):
    serializer = ConfirmationCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    confirmation_code = request.POST.get('confirmation_code')
    email = request.POST.get('email')
    if confirmation_code is None:
        return HttpResponse("Введите confirmation_code")
    if email is None:
        return HttpResponse("Введите email")
    user = get_object_or_404(User, email=email)
    token_check = default_token_generator.check_token(user, confirmation_code)
    if token_check is True:
        refresh = RefreshToken.for_user(user)
        return HttpResponse(
            f'refresh:{refresh}' + '\n' + f'access:{refresh.access_token}')
    return HttpResponse('Неправильный confirmation_code')


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    permission_classes = [IsAdmin, ]
    lookup_field = 'username'

    @action(detail=False, methods=['get', 'patch'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(role=user.role, partial=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoriesViewSet(viewsets.ModelViewSet):
    queryset = Categories.objects.all()
    lookup_field = 'slug'
    serializer_class = CategoriesSerializer
    permission_classes = [GeneralPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ('name',)

    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class GenresViewSet(viewsets.ModelViewSet):
    queryset = Genres.objects.all()
    lookup_field = 'slug'
    serializer_class = GenresSerializer
    permission_classes = [GeneralPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ('name',)

    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TitlesViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filter_class = ModelFilterTitles
    permission_classes = [GeneralPermission]

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return TitlesWriteSerializer
        return TitlesReadSerializer

    def get_queryset(self):
        return Titles.objects.all().annotate(rating=Avg('reviews__score'))


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorModerAdmin]

    def perform_create(self, serializer):
        review_id = self.kwargs['review_id']
        review = get_object_or_404(Reviews, pk=review_id)
        serializer.save(author=self.request.user, review_id=review.id)

    def get_queryset(self):
        review_id = self.kwargs['review_id']
        review = get_object_or_404(Reviews, pk=review_id)
        queryset = review.comments.all()
        return queryset


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewsSerializers
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorModerAdmin]

    def perform_create(self, serializer):
        title_id = self.kwargs['title_id']
        title = get_object_or_404(Titles, id=title_id)
        serializer.save(author=self.request.user, title=title)

    def get_queryset(self):
        title_id = self.kwargs['title_id']
        title = get_object_or_404(Titles, pk=title_id)
        queryset = title.reviews.all()
        return queryset