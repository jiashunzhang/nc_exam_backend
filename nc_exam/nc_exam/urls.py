#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""nc_exam URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from exam_admin import views as admin_views
from django.contrib import admin
from django.urls import path
from main import views as main_views

urlpatterns = [
    path('', main_views.weixin_main),
    path('login', main_views.login),
    path('getWorkTypeList', main_views.getWorkTypeList),
    path('getWorkShopList', main_views.getWorkShopList),
    path('getMyPaperTypes', main_views.getMyPaperTypes),
    path('getTestPapersByType', main_views.getTestPapersByType),
    path('getTestsByPaperID', main_views.getTestsByPaperID),
    path('getTestDetail', main_views.getTestDetail),
    path('getExamDetail', main_views.getExamDetail),
    path('getReadyInfo', main_views.getReadyInfo),
    path('getExamPapers', main_views.getExamPapers),
    path('getRandomTest', main_views.getRandomTest),
    path('getRandomExam', main_views.getRandomExam),
    path('ifNewUserLogin', main_views.ifNewUserLogin),
    path('getIndexInfo', main_views.getIndexInfo),
    path('registerNewUser', main_views.registerNewUser),
    path('handin', main_views.handin),
    path('handinExam', main_views.handinExam),
    path('getUndoneExamCount', main_views.getUndoneExamCount),
    path('admin/', admin.site.urls),
    path('exam_admin', admin_views.admin),
    path('getTopsComboData', admin_views.getTopsComboData),
    path('getTopsComboDataByPaper', admin_views.getTopsComboDataByPaper),
    path('getTopsList', admin_views.getTopsList),
    path('getMembers', admin_views.getMembers),
    path('getInfoTreeTop', admin_views.getInfoTreeTop),
    path('getMissedDetail', admin_views.getMissedDetail),
    path('getFailedDetail', admin_views.getFailedDetail),
    path('getScoreDetail', admin_views.getScoreDetail),
    path('getPaperTypeOptions', admin_views.getPaperTypeOptions),
    path('getPapersByTypeAdmin', admin_views.getPapersByTypeAdmin),
    path('getExamMembers', admin_views.getExamMembers),
    path('createExams', admin_views.createExams),
    path('uploadQuestionLibraryFile', admin_views.uploadQuestionLibraryFile),
    path('getQuestionsInfo', admin_views.getQuestionsInfo),
    path('saveEditedQuestion', admin_views.saveEditedQuestion),
    path('deletePaper', admin_views.deletePaper),
    path('newPaperType', admin_views.newPaperType),
    path('deletePaperType', admin_views.deletePaperType),
    path('modMember', admin_views.modMember),
    path('addMember', admin_views.addMember),
    path('getPaperImportLog', admin_views.getPaperImportLog)
]
