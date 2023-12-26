#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : server
# filename : filter
# author : ly_13
# date : 6/2/2023
import datetime
import json
import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated
from rest_framework.filters import BaseFilterBackend

from common.core.db.utils import RelatedManager
from system.models import UserInfo, DataPermission

logger = logging.getLogger(__name__)

class OwnerUserFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        if request.user and request.user.is_authenticated:
            return queryset.filter(creator_id=request.user)
        raise NotAuthenticated('未授权认证')


class DataPermissionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        1.获取所有数据权限规则
        2.循环判断规则
            a.循环判断最内层规则，根据模式和全部数据进行判断【如果规则数量为一个，则模式该规则链为或模式】
                如果模式为或模式，并存在全部数据，则该规则链其他规则失效，仅保留该规则
                如果模式为且模式，并且存在全部数据，则该改则失效
            b.判断外层规则 【如果规则数量为一个，则模式该规则链为或模式】
                若模式为或模式，并存在全部数据，则直接返回queryset
                若模式为且模式，则 返回queryset.filter(规则)
        """
        user_obj: UserInfo = request.user
        if user_obj.is_superuser:
            return queryset
        else:
            app_label = queryset.model._meta.app_label
            model_name = queryset.model._meta.model_name

        # table = f'*'
        dept_obj = user_obj.dept
        permission = DataPermission.objects.filter(is_active=True).filter(
            Q(userinfo=user_obj) | (Q(deptinfo=dept_obj) & Q(deptinfo__is_active=True)))
        results = []
        for obj in permission:
            rules = []
            if len(obj.rules) == 1:
                obj.mode_type = 0
            for rule in obj.rules:
                if rule.get('table') in [f"{app_label}.{model_name}", "*"]:
                    if rule.get('type') == 'value.all':
                        if obj.mode_type == 1:  # 且模式，存在*，则忽略该规则
                            continue
                        else:  # 或模式，存在* 则该规则表仅*生效
                            rules = [rule]
                            break
                    rules.append(rule)
            if rules:
                results.append({'mode': obj.mode_type, 'rules': rules})
        or_qs = []
        if not results:
            return queryset.none()
        for result in results:
            for rule in result.get('rules'):
                f_type = rule.get('type')
                if f_type == 'value.user.id':
                    rule['value'] = user_obj.id
                elif f_type == 'value.user.dept.id':
                    rule['value'] = user_obj.dept_id
                elif f_type == 'value.user.dept.ids':
                    rule['match'] = 'in'
                    rule['value'] = user_obj.dept.recursion_dept_info(dept_obj.pk)
                elif f_type == 'value.dept.ids':
                    rule['match'] = 'in'
                    rule['value'] = user_obj.dept.recursion_dept_info(json.loads(rule['value']))
                elif f_type == 'value.all':
                    rule['match'] = 'all'
                    if dept_obj.mode_type == 0 and result.get('mode') == 0:
                        logger.warning(f"{app_label}.{model_name} : all queryset")
                        return queryset  # 全部数据直接返回 queryset
                elif f_type == 'value.date':
                    val = json.loads(rule['value'])
                    if val < 0:
                        rule['value'] = timezone.now() - datetime.timedelta(seconds=-val)
                    else:
                        rule['value'] = timezone.now() + datetime.timedelta(seconds=val)
                elif f_type == 'value.json':
                    rule['value'] = json.loads(rule['value'])
                rule.pop('type', None)

            #  ((0, '或模式'), (1, '且模式'))
            qs = RelatedManager.get_filter_attrs_qs(result.get('rules'))
            q = Q()
            if result.get('mode') == 1:
                for a in set(qs):
                    if a == Q():
                        continue
                    q &= a
            else:
                for a in set(qs):
                    if a == Q():
                        q = Q()
                        break
                    q |= a
            or_qs.append(q)
        q1 = Q()
        for q in set(or_qs):
            if dept_obj.mode_type == 1:
                if q == Q():
                    continue
                q1 &= q
            else:
                if q == Q():
                    return queryset
                q1 |= q
        if dept_obj.mode_type == 1 and q1 == Q():
            return queryset.none()

        logger.warning(f"{app_label}.{model_name} : {q1}")
        return queryset.filter(q1)
