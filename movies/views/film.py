#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : film
# author : ly_13
# date : 11/20/2023
import json
import logging

from django.conf import settings
from django.db.models import Q, FileField
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter

from common.core.modelset import BaseModelSet
from common.core.response import ApiResponse
from movies.models import FilmInfo, Category, EpisodeInfo, WatchHistory
from movies.utils.serializer import FilmInfoSerializer, CategorySerializer, EpisodeInfoSerializer, \
    CategoryListSerializer, WatchHistorySerializer

logger = logging.getLogger(__file__)


class FilmFilter(filters.FilterSet):
    language = filters.CharFilter(field_name='language', lookup_expr='icontains')
    subtitles = filters.CharFilter(field_name='subtitles', lookup_expr='icontains')
    director = filters.CharFilter(field_name='director', lookup_expr='icontains')
    starring = filters.CharFilter(field_name='starring', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')
    enable = filters.BooleanFilter(field_name='enable')

    name = filters.NumberFilter(field_name="name", method='name_filter')
    categories = filters.CharFilter(field_name="categories", method='categories_filter')

    def name_filter(self, queryset, name, value):
        if value:
            return queryset.filter(Q(name__icontains=value) | Q(title__icontains=value))
        return queryset

    def categories_filter(self, queryset, name, value):
        category = json.loads(value)
        if category:
            return queryset.filter(category__in=json.loads(value))
        return queryset

    class Meta:
        model = FilmInfo
        fields = ['id']


class FilmInfoView(BaseModelSet):
    queryset = FilmInfo.objects.all().distinct()
    serializer_class = FilmInfoSerializer

    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['views', 'created_time', 'rate', 'times']
    filterset_class = FilmFilter

    def list(self, request, *args, **kwargs):
        data = super().list(request, *args, **kwargs).data
        return ApiResponse(**data,
                           category=CategoryListSerializer(Category.objects.filter(enable=True).all(), many=True).data)

    @action(methods=['post'], detail=True)
    def upload(self, request, *args, **kwargs):
        files = request.FILES.getlist('file', [])
        instance = self.get_object()
        file_obj = files[0]
        try:
            file_type = file_obj.name.split(".")[-1]
            if file_type not in ['png', 'jpeg', 'jpg', 'gif']:
                logger.error(f"user:{request.user} upload file type error file:{file_obj.name}")
                raise
            if file_obj.size > settings.FILE_UPLOAD_SIZE:
                return ApiResponse(code=1003, detail=f"图片大小不能超过 {settings.FILE_UPLOAD_SIZE}")
        except Exception as e:
            logger.error(f"user:{request.user} upload file type error Exception:{e}")
            return ApiResponse(code=1002, detail="错误的图片类型")
        delete_avatar_name = None
        if instance.poster:
            delete_avatar_name = instance.poster.name
        instance.poster = file_obj
        instance.save(update_fields=['poster'])
        if delete_avatar_name:
            FileField(name=delete_avatar_name).storage.delete(delete_avatar_name)
        return ApiResponse()


class EpisodeInfoFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    film_id = filters.NumberFilter(field_name='film')
    enable = filters.BooleanFilter(field_name='enable')

    class Meta:
        model = EpisodeInfo
        fields = ['id']


class EpisodeInfoView(BaseModelSet):
    queryset = EpisodeInfo.objects.all().distinct()
    serializer_class = EpisodeInfoSerializer

    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['rank', 'created_time']
    filterset_class = EpisodeInfoFilter

    @action(methods=['post'], detail=False)
    def action_rank(self, request, *args, **kwargs):
        pks = request.data.get('pks', [])
        film = request.data.get('film')
        rank = 1
        for pk in pks:
            EpisodeInfo.objects.filter(film=film, pk=pk).update(rank=rank)
            rank += 1
        return ApiResponse(detail='播放顺序保存成功')


class CategoryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    enable = filters.BooleanFilter(field_name='enable')

    class Meta:
        model = Category
        fields = ['id']


class CategoryView(BaseModelSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_time']
    filterset_class = CategoryFilter


class WatchHistoryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='episode__name', lookup_expr='icontains')
    owner = filters.NumberFilter(field_name='owner__id')

    class Meta:
        model = WatchHistory
        fields = ['id']


class WatchHistoryView(BaseModelSet):
    queryset = WatchHistory.objects.all()
    serializer_class = WatchHistorySerializer

    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_time', 'times']
    filterset_class = WatchHistoryFilter

    def create(self, request, *args, **kwargs):
        return ApiResponse(detail="禁止操作")

    def update(self, request, *args, **kwargs):
        return ApiResponse(detail="禁止操作")

    @action(methods=['post'], detail=False)
    def times(self, request, *args, **kwargs):
        times = request.data.get('times')
        file_id = request.data.get('file_id')
        episode = EpisodeInfo.objects.filter(files_id=file_id).first()
        if times and episode:
            WatchHistory.objects.update_or_create(defaults={'times': times}, owner=request.user, episode=episode)
        return ApiResponse()