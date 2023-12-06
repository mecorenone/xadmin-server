#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : server
# filename : user
# author : ly_13
# date : 6/16/2023
import logging

from rest_framework.decorators import action

from common.core.modelset import OwnerModelSet, UploadFileAction
from common.core.response import ApiResponse
from system.utils.serializer import UserInfoSerializer

logger = logging.getLogger(__name__)


class UserInfoView(OwnerModelSet, UploadFileAction):
    serializer_class = UserInfoSerializer
    FILE_UPLOAD_FIELD = 'avatar'

    def get_object(self):
        return self.request.user

    @action(methods=['post'], detail=False)
    def reset_password(self, request, *args, **kwargs):
        old_password = request.data.get('old_password')
        sure_password = request.data.get('sure_password')
        if old_password and sure_password:
            instance = self.get_object()
            if not instance.check_password(old_password):
                return ApiResponse(code=1001, detail='旧密码校验失败')
            instance.set_password(sure_password)
            instance.save(update_fields=['password'])
            return ApiResponse()
        return ApiResponse(code=1001, detail='修改失败')
