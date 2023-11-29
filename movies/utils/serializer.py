#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : serializer
# author : ly_13
# date : 11/17/2023

import logging
from collections import OrderedDict

from rest_framework import serializers

from movies.models import AliyunDrive, AliyunFile, FilmInfo, Category, EpisodeInfo, WatchHistory

logger = logging.getLogger(__file__)


class AliyunDriveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AliyunDrive
        fields = ['pk', 'owner', 'user_name', 'nick_name', 'user_id', 'default_drive_id', 'default_sbox_drive_id',
                  'avatar', 'expire_time', 'x_device_id', 'used_size', 'total_size', 'description', 'enable', 'private',
                  'active', 'created_time', 'updated_time']
        read_only_fields = list(
            set([x.name for x in AliyunDrive._meta.fields]) - {"enable", "private", "description"})


class AliyunFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AliyunFile
        fields = ['pk', 'aliyun_drive', 'name', 'file_id', 'created_time', 'size', 'content_type', 'category',
                  'downloads', 'description', 'used', 'duration']
        read_only_fields = list(set([x.name for x in AliyunFile._meta.fields]) - {"description"})

    used = serializers.SerializerMethodField()

    def get_used(self, obj):
        return hasattr(obj, 'episodeinfo')


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['value', 'label']
        read_only_fields = list(set([x.name for x in Category._meta.fields]))

    value = serializers.IntegerField(source='id')
    label = serializers.CharField(source='name')


class FilmInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilmInfo
        fields = ['pk', 'name', 'title', 'poster', 'category', 'region', 'language', 'subtitles', 'director',
                  'starring', 'times', 'views', 'rate', 'description', 'enable', 'created_time', 'updated_time',
                  'category_info']
        extra_kwargs = {'pk': {'read_only': True}, 'poster': {'read_only': True}}
        # read_only_fields = list(set([x.name for x in FilmInfo._meta.fields]) - {"pk", "views"})

    category_info = serializers.SerializerMethodField(read_only=True)

    def get_category_info(self, obj):
        result = []
        if isinstance(obj, OrderedDict):
            queryset = obj.get('category')
        else:
            queryset = obj.category.all()
        if queryset:
            for objs in queryset:
                result.append({'pk': objs.pk, 'name': objs.name})
        return result


class EpisodeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpisodeInfo
        fields = ['pk', 'name', 'files', 'enable', 'created_time', 'updated_time', 'file_id', 'film', 'views', "rank"]
        extra_kwargs = {'pk': {'read_only': True}, 'files': {'read_only': True}}
        read_only_fields = ("pk", "files", "rank")

    file_id = serializers.CharField(write_only=True)

    def validate(self, attrs):
        ali_file = AliyunFile.objects.filter(file_id=attrs.pop('file_id')).first()
        attrs['files'] = ali_file
        if not attrs['name'] and ali_file:
            attrs['name'] = ali_file.name
        return attrs

    files = serializers.SerializerMethodField()

    def get_files(self, obj):
        return {'pk': obj.files.pk, 'file_id': obj.files.file_id, 'name': obj.files.name,
                'duration': obj.files.duration}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'created_time', 'pk', 'description', 'enable', 'count']

    count = serializers.SerializerMethodField()

    def get_count(self, obj):
        return obj.filminfo_set.count()


class WatchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchHistory
        fields = ['created_time', 'pk', 'times', 'owner', 'episode', 'updated_time']

    owner = serializers.SerializerMethodField()
    episode = serializers.SerializerMethodField()

    def get_owner(self, obj):
        return {'pk': obj.owner.pk, 'username': obj.owner.username}

    def get_episode(self, obj):
        times = obj.episode.files.duration if obj.episode.files.duration else obj.episode.film.times
        return {'pk': obj.episode.pk, 'name': obj.episode.name, 'film_name': obj.episode.film.name,
                'times': times, 'film_pk': obj.episode.film.pk}