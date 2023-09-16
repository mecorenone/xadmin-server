#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : server
# filename : serializer
# author : ly_13
# date : 6/6/2023
import os.path
from typing import OrderedDict

from django.conf import settings
from rest_framework import serializers

from system import models


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserInfo
        fields = ['username', 'nickname', 'email', 'last_login', 'sex', 'date_joined', 'pk', 'mobile',
                  'is_active', 'roles', 'avatar', 'roles_info', 'remark']
        extra_kwargs = {'last_login': {'read_only': True}, 'date_joined': {'read_only': True},
                        'pk': {'read_only': True}, 'avatar': {'read_only': True}, 'roles': {'read_only': True}}
        # extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ['pk'] + list(set([x.name for x in models.UserInfo._meta.fields]) - set(fields))

    roles_info = serializers.SerializerMethodField(read_only=True)

    def get_roles_info(self, obj):
        result = []
        if isinstance(obj, OrderedDict):
            role_queryset = obj.get('roles')
        else:
            role_queryset = obj.roles.all()
        if role_queryset:
            for role in role_queryset:
                result.append({'pk': role.pk, 'name': role.name})
        return result


class UserInfoSerializer(UserSerializer):
    class Meta:
        model = models.UserInfo
        fields = ['username', 'nickname', 'email', 'last_login', 'sex', 'pk', 'mobile', 'avatar', 'roles_info',
                  'date_joined']
        extra_kwargs = {'last_login': {'read_only': True}, 'date_joined': {'read_only': True},
                        'pk': {'read_only': True}, 'avatar': {'read_only': True}}
        read_only_fields = ['pk'] + list(set([x.name for x in models.UserInfo._meta.fields]) - set(fields))


class RouteMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenuMeta
        fields = ['title', 'icon', 'showParent', 'showLink', 'extraIcon', 'keepAlive', 'frameSrc', 'frameLoading',
                  'transition', 'hiddenTag', 'dynamicLevel', 'auths']

    showParent = serializers.BooleanField(source='is_show_parent', read_only=True)
    showLink = serializers.BooleanField(source='is_show_menu', read_only=True)
    extraIcon = serializers.CharField(source='r_svg_name', read_only=True)
    keepAlive = serializers.BooleanField(source='is_keepalive', read_only=True)
    frameSrc = serializers.CharField(source='frame_url', read_only=True)
    frameLoading = serializers.BooleanField(source='frame_loading', read_only=True)

    transition = serializers.SerializerMethodField()

    def get_transition(self, obj):
        return {
            'enterTransition': obj.transition_enter,
            'leaveTransition': obj.transition_leave,
        }

    hiddenTag = serializers.BooleanField(source='is_hidden_tag', read_only=True)
    dynamicLevel = serializers.IntegerField(source='dynamic_level', read_only=True)

    auths = serializers.SerializerMethodField()

    def get_auths(self, obj):
        user = self.context.get('user')
        if user.is_superuser:
            menu_obj = models.Menu.objects
        else:
            menu_obj = models.Menu.objects.filter(userrole__in=user.roles.all()).distinct()
        queryset = menu_obj.filter(menu_type=2, parent=obj.menu, is_active=True).values('name').distinct()
        return [x['name'] for x in queryset]


class MenuMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenuMeta
        fields = '__all__'


class MenuSerializer(serializers.ModelSerializer):
    meta = MenuMetaSerializer()

    class Meta:
        model = models.Menu
        fields = ['pk', 'name', 'rank', 'path', 'component', 'meta', 'parent', 'menu_type', 'is_active']
        read_only_fields = ['pk']
        extra_kwargs = {'rank': {'read_only': True}}

    def update(self, instance, validated_data):
        serializer = MenuMetaSerializer(instance.meta, data=validated_data.pop('meta'), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return super().update(instance, validated_data)

    def create(self, validated_data):
        serializer = MenuMetaSerializer(data=validated_data.pop('meta'))
        serializer.is_valid(raise_exception=True)
        validated_data['meta'] = serializer.save()
        return super().create(validated_data)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserRole
        fields = ['pk', 'name', 'is_active', 'code', 'menu', 'description', 'created_time']
        read_only_fields = ['pk']


class RouteSerializer(MenuSerializer):
    meta = RouteMetaSerializer()


class OperationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperationLog
        fields = ["pk", "owner", "module", "path", "body", "method", "ipaddress", "browser", "system", "response_code",
                  "response_result", "status_code", "created_time"]
        read_only_fields = ["pk"] + list(set([x.name for x in models.OperationLog._meta.fields]))

    owner = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()

    def get_owner(self, obj):
        if obj.owner:
            return {'pk': obj.owner.pk, 'username': obj.owner.username}
        return {}

    def get_module(self, obj):
        module_name = obj.module
        map_module_name = settings.API_MODEL_MAP.get(obj.path, None)
        if not module_name and map_module_name:
            return map_module_name
        return module_name


class UploadFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UploadFile
        fields = ['pk', 'filepath', 'filename', 'filesize']
        read_only_fields = [x.name for x in models.UploadFile._meta.fields]


class NoticeMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NoticeMessage
        fields = ['pk', 'level', 'title', 'message', "created_time", "owner", "user_count", "read_user_count",
                  'notice_type', 'extra_json', "files", "owners", "publish", 'notice_type_display']

        read_only_fields = ['pk', 'owner']

    notice_type_display = serializers.CharField(source="get_notice_type_display", read_only=True)
    owners = serializers.JSONField(write_only=True)
    files = serializers.JSONField(write_only=True)

    user_count = serializers.SerializerMethodField(read_only=True)
    read_user_count = serializers.SerializerMethodField(read_only=True)

    def get_read_user_count(self, obj):
        if obj.notice_type in [0, 1]:
            return models.NoticeUserRead.objects.filter(notice=obj, unread=False, owner_id__in=obj.owner.all()).count()

        elif obj.notice_type == 2:
            return obj.owner.count()

        return 0

    def get_user_count(self, obj):
        return obj.owner.count()

    def validate(self, attrs):
        notice_type = attrs.get('notice_type')
        owners = attrs.get('owners')
        if notice_type == 1 and not owners:
            raise Exception('消息通知缺少用户')
        if notice_type == 2 and owners:
            attrs.pop('owners')

        files = attrs.get('files')
        if files is not None:
            del attrs['files']
            attrs['file'] = models.UploadFile.objects.filter(
                filepath__in=[file.replace(os.path.join('/', settings.MEDIA_URL), '') for file in files],
                owner=self.context.get('request').user).all()
        return attrs

    def create(self, validated_data):
        owners = []
        if validated_data.get('owners') is not None:
            owners = validated_data.pop('owners')
        instance = super().create(validated_data)
        instance.file.filter(is_tmp=True).update(is_tmp=False)
        if owners and validated_data['notice_type'] in [0, 1]:
            instance.owner.set(models.UserInfo.objects.filter(pk__in=owners))
        return instance

    def update(self, instance, validated_data):
        validated_data.pop('notice_type')  # 不能修改消息类型
        o_files = [x['pk'] for x in instance.file.all().values('pk')]
        n_files = []
        if validated_data.get('file'):
            n_files = [x['pk'] for x in validated_data.get('file').values('pk')]

        instance = super().update(instance, validated_data)
        if instance:
            instance.file.filter(is_tmp=True).update(is_tmp=False)
            del_files = set(o_files) - set(n_files)
            if del_files:
                for file in models.UploadFile.objects.filter(pk__in=del_files, owner=self.context.get('request').user):
                    file.delete()  # 这样操作，才可以同时删除底层的文件，如果直接 queryset 进行delete操作，则不删除底层文件
        return instance


class UserNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NoticeMessage
        fields = ['pk', 'level', 'title', 'message', "created_time", 'notice_type_display', 'unread']
        read_only_fields = ['pk', 'owner']

    notice_type_display = serializers.CharField(source="get_notice_type_display", read_only=True)
    unread = serializers.SerializerMethodField()

    def get_unread(self, obj):
        queryset = models.NoticeUserRead.objects.filter(notice=obj, owner=self.context.get('request').user)
        if obj.notice_type in [0, 1]:
            return bool(queryset.filter(unread=True).count())
        elif obj.notice_type == 2:
            return not bool(queryset.count())
        return True


class NoticeUserReadMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NoticeUserRead
        fields = ['pk', 'owner_info', 'notice_info', "updated_time", "unread"]
        read_only_fields = [x.name for x in models.NoticeUserRead._meta.fields]
        # depth = 1

    owner_info = serializers.SerializerMethodField()
    notice_info = serializers.SerializerMethodField()

    def get_owner_info(self, obj):
        return {'pk': obj.owner.pk, 'username': obj.owner.username}

    def get_notice_info(self, obj):
        return NoticeMessageSerializer(obj.notice).data
