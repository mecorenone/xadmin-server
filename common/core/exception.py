#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : server
# filename : exception
# author : ly_13
# date : 6/2/2023
from logging import getLogger

from rest_framework.exceptions import Throttled, APIException
from rest_framework.views import exception_handler
from rest_framework.views import set_rollback

from common.core.response import ApiResponse

logger = getLogger('drf_exception')
unexpected_exception_logger = getLogger('unexpected_exception')


def common_exception_handler(exc, context):
    # context['view']  是TextView的对象，想拿出这个对象对应的类名
    ret = exception_handler(exc, context)  # 是Response对象，它内部有个data
    logger.error(f'{context["view"].__class__.__name__} ERROR: {exc} ret:{ret}')
    if isinstance(exc, Throttled):
        second = f' {exc.wait} 秒之后'
        if not exc.wait:
            second = '稍后'
        ret.data = {
            'code': 999,
            'detail': f'您手速太快啦，请{second}再次访问',
        }

    elif isinstance(exc, APIException):

        if isinstance(exc.detail, (list, dict)):
            ret.data = exc.detail
        else:
            ret.data = {'detail': exc.detail}
        set_rollback()
    else:
        unexpected_exception_logger.exception('')

    if not ret:  # drf内置处理不了，丢给django 的，我们自己来处理
        return ApiResponse(detail=str(exc), code=500, status=500)
    else:
        if not ret.data.get('detail'):
            ret.data['detail'] = str(exc)
        ret.data['status'] = ret.status_code
        ret.data['code'] = ret.status_code
        return ApiResponse(**ret.data)
