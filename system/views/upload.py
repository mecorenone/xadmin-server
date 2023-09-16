#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin_server
# filename : upload
# author : ly_13
# date : 6/26/2023
import logging

from rest_framework.views import APIView

from common.core.response import ApiResponse
from system.models import UploadFile, UserInfo
from system.utils.serializer import UploadFileSerializer

logger = logging.getLogger(__file__)


class UploadView(APIView):

    def post(self, request):
        """
        该方法 主要是本地上传文件接口
        :param request:
        :return:
        """
        # 获取多个file
        files = request.FILES.getlist('file', [])
        user_obj = request.user
        uid = request.query_params.get('uid')
        if user_obj and uid:
            user_obj = UserInfo.objects.filter(pk=uid).first()
        if user_obj:
            if user_obj.pk <= 2:
                return ApiResponse(code=1004, detail='默认用户信息禁止操作')

        result = []
        for file_obj in files:
            try:
                file_type = file_obj.name.split(".")[-1]
                # if file_type not in ['png', 'jpeg', 'jpg', 'gif']:
                #     logger.error(f"user:{request.user} upload file type error file:{file_obj.name}")
                #     raise
            except Exception as e:
                logger.error(f"user:{request.user} upload file type error Exception:{e}")
                return ApiResponse(code=1002, detail="错误的文件类型")
            obj = UploadFile.objects.create(owner=request.user, filename=file_obj.name, filesize=file_obj.size,
                                            filepath=file_obj)
            result.append(obj)
        return ApiResponse(data=UploadFileSerializer(result, many=True).data)
