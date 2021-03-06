#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib, os, requests, logging, calendar, datetime, math, decimal, requests, uuid, sys, random
import simplejson as json
from lxml import etree
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from configparser import ConfigParser
#from WXBizDataCrypt import WXBizDataCrypt
#from main.models import Department, Members, WorkType, Questions, TestPapers, TestQuestions, Papers, PaperTypes, Position, ExamPapers, \
#                        ExamQuestions, SignInLog, TestRedPackets, RedPacketType, AccumulatePoints, AccumulatePointsType, AccumulatePointsLog
from main.models import *
from django.db.models import Q, Count, Avg, Sum
from django.db import connection, transaction

WEIXIN_TOKEN = 'carzpurzkey_nc_exam_weixin_token'

config = ConfigParser()
config.read(os.path.dirname(__file__) + '/config.ini')

question_type_map = { '1': '单选题', '2': '多选题', '3': '判断题' }

@csrf_exempt
def weixin_main(request):
    """
    微信接入验证是GET方法，微信正常的收发消息是POST方法
    """
    if request.method == 'GET':
        signature = request.GET.get('signature', None)
        timestamp = request.GET.get('timestamp', None)
        nonce = request.GET.get('nonce', None)
        echostr = request.GET.get('echostr', None)

        token = WEIXIN_TOKEN

        tmp_list = [token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = '%s%s%s' % tuple(tmp_list)
        tmp_str = hashlib.sha1(tmp_str.encode('utf8')).hexdigest()
        if tmp_str == signature:
            return HttpResponse(echostr)
        else:
            return HttpResponse('weixin index')
@csrf_exempt
def login(request):
    appid = config.get('WeiXin', 'appid')
    appsecret = config.get('WeiXin', 'appsecret')
    code = request.GET['code']
    jscode2session_url = config.get('WeiXin', 'jscode2session_url')

    if code:
        req_code_params = {'appid': appid, 'secret': appsecret, 'js_code': code, 'grant_type': 'authorization_code'}
        resp = requests.get(jscode2session_url, params=req_code_params)
        resp_obj = resp.json()

        if 'errcode' in resp_obj:
            return HttpResponse('{ \"errmsg\": \"%s\" }' % resp_obj['errmsg'], content_type='text/json')
        if 'openid' not in resp_obj:
            return HttpResponse('{ \"errmsg\": \"服务器返回异常。\" }', content_type='text/json')
        if not resp_obj['openid']:
            return HttpResponse('{ \"errmsg\": \"未能从腾讯获取用户微信ID。\" }', content_type='text/json')

        request.session['open_id'] = resp_obj['openid']
        request.session.save()
        if not Members.objects.filter(weixin_open_id=resp_obj['openid']).exists():
            request.session['wx_session_key'] = resp_obj['session_key']
            return HttpResponse('{ \"errmsg": \"nosuchmember\", \"my_session_key\": \"%s\" }' % request.session.session_key, content_type='text/json')

        if Members.objects.filter(Q(weixin_open_id=resp_obj['openid']), Q(deleted=True)).exists():
            return HttpResponse('{ \"errmsg": \"deletedmember\" }', content_type='text/json')

        if Members.objects.filter(Q(weixin_open_id=resp_obj['openid']), Q(verified=False)).exists():
            return HttpResponse('{ \"errmsg\": \"notverified\" }', content_type='text/json')

        mem = Members.objects.get(weixin_open_id=resp_obj['openid'])

        request.session['wx_session_key'] = resp_obj['session_key']
        return HttpResponse('{ \"my_session_key\": \"%s\", \"mem_name\": \"%s\", \"mem_dep\": \"%s\", \"mem_wt\": \"%s\", \"mem_pos\": \"%s\" }' % (request.session.session_key, mem.name, mem.dep_id.dep_name, mem.work_type_id.type_name, mem.position_id.name), content_type='text/json')
    else:
        return HttpResponse('{ \"errmsg\": \"服务器未返回code。\" }', content_type='text/json')

@csrf_exempt
def ifNewUserLogin(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"openidlost\" }', content_type='text/json')

    try:
        if not Members.objects.filter(weixin_open_id=woi).exists():
            return HttpResponse('{ \"errmsg\": \"newuser\" }', content_type='text/json')
        else:
            return HttpResponse('{ \"errmsg\": \"OK\" }', content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getWorkTypeList(request):
    ret_list = list()

    try:
        for wt in WorkType.objects.all():
            ret_list.append({ 'id': wt.work_type_id, 'name': wt.type_name })

        return HttpResponse(json.dumps({ 'work_types': ret_list }), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"无法获取工种列表：%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getWorkShopList(request):
    ret_list = list()

    try:
        for dep in Department.objects.all().order_by('level'):
            ret_list.append({ 'id': dep.dep_id, 'name': dep.dep_name })

        return HttpResponse(json.dumps({ 'workshops': ret_list }), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"无法获取车间列表：%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getMyPaperTypes(request):
    if_exam = request.POST.get('if_exam', 0)

    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"notloggedin\" }', content_type='text/json')

    try:
        with connection.cursor() as cursor:
            cursor.callproc('get_paper_type_by_user', (request.session['open_id'], False if if_exam == '0' else True))
            ret = dictfetchall(cursor)

        #if not ret:
        #    ret = list()
        #    pts = PaperTypes.objects.all()
        #    for pt in pts:
        #        m = Members.objects.get(weixin_open_id=woi)
        #        if not m:
        #            return HttpResponse('{ \"errmsg\": \"没有此用户。\" }', content_type='text/json')

        #        paper_count = Papers.objects.filter(type_id=pt).count()
        #        ret.append({ 'type_name': pt.name, 'max_score': 0, 'paper_count': paper_count, 'weixin_open_id': m.weixin_open_id, 'type_id': pt.type_id })

        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getTestPapersByType(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"nologgedin\" }', content_type='text/json')

    type_id = request.POST.get('type_id', None)

    if not type_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }')

    try:
        m = Members.objects.get(weixin_open_id=woi)
        if not m:
            return HttpResponse('{ \"errmsg\": \"无此用户。\" }', content_type='text/json')

        wti = m.work_type_id
        with connection.cursor() as cursor:
            cursor.callproc('get_test_papers_by_type', (type_id, wti.work_type_id, woi))
            ret = dictfetchall(cursor)

        if not ret:
            pt = PaperTypes.objects.get(type_id=type_id)
            if not pt:
                return HttpResponse('{ \"errmsg\": \"无此类试卷。\" }', content_type='text/json')
            papers = Papers.objects.filter(work_type_id=wti, type_id=pt)

            ret = list()

            for p in papers:
                ret.append({ 'max_score': 0, 'type_id': p.type_id.type_id, 'passed_time': 0, 'paper_id': p.paper_id, 'paper_name': p.paper_name, 'set_date': p.set_date.strftime('%Y年%m月%d日'), 'test_time': '无', 'passing_score': p.passing_score, 'test_count': 0, 'test_time': p.test_time })

        return HttpResponse(json.dumps(ret, cls=DateTimeJSONEncoder))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getReadyInfo(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息已过期，请重新登录。\" }', content_type='text/json')

    try:
        m = Members.objects.get(weixin_open_id=woi)
        if not m:
            return HttpResponse('{ \"errmsg\": \"用户信息丢失。\" }', content_type='text/json')

        return HttpResponse('{ \"mem_name\": \"%s\", \"workshop\": \"%s\", \"work_type\": \"%s\" }' % (m.name, m.dep_id.dep_name, m.work_type_id.type_name), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getExamPapers(request):
    done = request.POST.get('done', '0')

    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"nologgedin\" }', content_type='text/json')

    try:
        m = Members.objects.get(weixin_open_id=woi)
        if not m:
            return HttpResponse('{ \"errmsg\": \"无此用户。\" }', content_type='text/json')

        if done == '0':
            papers = ExamPapers.objects.filter(done=False, weixin_open_id=woi, avail_start__lte=datetime.datetime.now(), avail_end__gte=datetime.datetime.now())
        else:
            papers = ExamPapers.objects.filter(done=True, weixin_open_id=woi)
        
        ret = list()
        for p in papers:
            ret.append({ 'passing_score': p.passing_score,
                        'exam_time': p.exam_time,
                        'exam_paper_id': p.exam_paper_id,
                        'paper_name': p.name,
                        'set_date': p.date_time.strftime('%Y年%m月%d日'),
                        'done_date': p.done_date.strftime('%Y年%m月%d日') if p.done_date else '尚未考试',
                        'score': math.floor(p.score),
                        'ss_count': p.ss_count,
                        'ms_count': p.ms_count,
                        'jm_count': p.jm_count })

        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getTestsByPaperID(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"nologgedin\" }', content_type='text/json')

    paper_id = request.POST.get('paper_id', None)
    if not paper_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }')

    try:
        with connection.cursor() as cursor:
            cursor.callproc('get_tests_by_paperid', (paper_id, request.session['open_id']))
            ret = dictfetchall(cursor)
        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getTestDetail(request):
    test_paper_id = request.POST.get('test_paper_id', None)
    if not test_paper_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\"}')

    try:
        with connection.cursor() as cursor:
            cursor.callproc('get_test_questions', (test_paper_id,))
            ret = dictfetchall(cursor)
        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e))

@csrf_exempt
def getExamDetail(request):
    exam_paper_id = request.POST.get('exam_paper_id', None)
    if not exam_paper_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\"}', content_type='text/json')

    try:
        with connection.cursor() as cursor:
            cursor.callproc('get_exam_questions', (exam_paper_id,))
            ret = dictfetchall(cursor)
        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getRandomTest(request):
    paper_id = request.POST.get('paper_id', None)
    if not paper_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }')

    try:
        with connection.cursor() as cursor:
            cursor.callproc('get_random_test', (paper_id,))
            ret = dictfetchall(cursor)
        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e))

@csrf_exempt
def getRandomExam(request):
    exam_paper_id = request.POST.get('exam_paper_id', None)
    if not exam_paper_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    try:
        exam_paper = ExamPapers.objects.get(exam_paper_id=exam_paper_id)
        if not exam_paper:
            return HttpResponse('{ \"errmsg\": \"您无权参加此考试。\" }', content_type='text/json')
        debugLog(exam_paper.done)
        if exam_paper.done:
            return HttpResponse('{ \"errmsg\": \"您已参加过此考试，请不要重复参考。\" }', content_type='text/json')

        with connection.cursor() as cursor:
            cursor.callproc('get_random_exam', (exam_paper.paper_ids, exam_paper.ss_count, exam_paper.ms_count, exam_paper.jm_count))
            ret = dictfetchall(cursor)
        return HttpResponse(json.dumps(ret))
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getIndexInfo(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"notloggedin\" }')

    try:
        cur_year = datetime.date.today().year
        cur_month = datetime.date.today().month
        monthRange = calendar.monthrange(cur_year, cur_month)[1]
        firstDay = datetime.datetime(cur_year, cur_month, 1, 0, 0, 0)
        lastDay = datetime.datetime(cur_year, cur_month, monthRange, 23, 59, 59)

        tests_count = TestPapers.objects.filter(weixin_open_id=woi, date_time__gte=firstDay, date_time__lte=lastDay).count()
        #debugLog(str(TestPapers.objects.filter(weixin_open_id=woi, date_time__gte=firstDay, date_time__lte=lastDay).annotate(tests_count=Count('test_paper_id')).query))

        avg_score = TestPapers.objects.filter(weixin_open_id=woi, date_time__gte=firstDay, date_time__lte=lastDay)
        if not avg_score or not avg_score.exists():
            avg_score = 0
        else:
            avg_score = avg_score.aggregate(avg_score=Avg('score'))['avg_score']

        mem_obj = Members.objects.filter(weixin_open_id=woi).first()
        mem_wti = mem_obj.work_type_id.work_type_id
        mem_name = mem_obj.name
        mem_pos_name = mem_obj.position_id.name
        mem_dep_name = mem_obj.dep_id.dep_name
        mem_allow_rp = (1 if mem_obj.allow_red_packet else 0)

        mem_wtn = WorkType.objects.filter(work_type_id=mem_wti).first().type_name
        
        nbs = NoticeBoard.objects.filter(nb_type=1, date_start__lte=datetime.datetime.now(), date_stop__gte=datetime.datetime.now()).order_by('-date_time')[:10]
        rp_nbs = NoticeBoard.objects.filter(nb_type=2, date_start__lte=datetime.datetime.now(), date_stop__gte=datetime.datetime.now()).order_by('-date_time')[:10]
        nbs_ret = list()
        for nb in nbs:
            nbs_ret.append({
                'content': nb.content,
                'color': nb.color
            })
        rpnb_ret = list()
        for rnb in rp_nbs:
            rpnb_ret.append({
                'content': rnb.content,
                'color': rnb.color
            })
        ret = '{ \"tests_count\": \"%s\", \"avg_score\": \"%s\", \"mem_name\": \"%s\", \"mem_wtn\": \"%s\", \"mem_pos\": \"%s\", \"mem_dep\": \"%s\", \"mem_allow_rp\": \"%s\", \"nb\": %s, \"rnb\": %s }' % (tests_count, avg_score, mem_name, mem_wtn, mem_pos_name, mem_dep_name, mem_allow_rp, json.dumps(nbs_ret), json.dumps(rpnb_ret))
        return HttpResponse(ret, content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def registerNewUser(request):
    #name = request.POST.get('name', None)
    #worktype = request.POST.get('worktype', None)
    #workshop = request.POST.get('workshop', None)
    idcard = request.POST.get('idcard', None)
    phonenumber = request.POST.get('phonenumber', None)
    woi = request.session.get('open_id', None)

    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    #if not name or not worktype or not workshop or not idcard:
    if not idcard:
        return HttpResponse('{ \"errmsg\": \"请至少填写身份证号码。\" }', content_type='text/json')

    try:
        #nu_wt = WorkType.objects.get(work_type_id=int(worktype))
        #if not nu_wt:
        #    return HttpResponse('{ \"errmsg\": \"无此工种。\" }', content_type='text/json')

        #nu_ws = Department.objects.get(dep_id=int(workshop))
        #if not nu_ws:
        #    return HttpResponse('{ \"errmsg\": \"无此车间。\" }', content_type='text/json')

        #new_user = Members()
        #new_user.name = name
        #new_user.work_type_id = nu_wt
        #new_user.idcard = idcard
        #new_user.dep_id = nu_ws
        #new_user.phone_number = phonenumber
        #new_user.verified = False
        #new_user.deleted = False
        #new_user.weixin_open_id = woi
        #new_user.save()
        if not Members.objects.filter(idcard=idcard).exists():
            return HttpResponse('{ \"errmsg\": \"您还没有在系统中登记，请联系教育科管理员。\" }', content_type='text/json')

        mem = Members.objects.get(idcard=idcard)
        if mem.weixin_open_id:
            if mem.weixin_open_id != woi:
                return HttpResponse('{ \"errmsg\": \"您的身份证已绑定了其他微信号，请联系教育科管理员。\" }', content_type='text/json')
            else:
                return HttpResponse('{ \"errmsg\": \"您的身份证已和您的微信号绑定，请不要重复绑定。\" }', content_type='text/json')

        mem.weixin_open_id = woi
        if phonenumber:
            mem.phone_number = phonenumber
        mem.verified = True
        mem.deleted = False
        mem.save()

        return HttpResponse('{ \"errmsg\": \"OK\" }', content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def handin(request):
    paper_id = request.POST.get('paper_id', None)
    if_exam = request.POST.get('if_exam', None)
    paper_detail = request.POST.get('paper_detail', None)
    if not paper_id or not if_exam or not paper_detail:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    me = Members.objects.get(weixin_open_id=woi, deleted=0, verified=1)
    if not me:
        return HttpResponse('{ \"errmsg\": \"该用户不存在。\" }', content_type='text/json')

    try:
        pid_obj = Papers.objects.get(paper_id=paper_id)
        if not pid_obj:
            return HttpResponse('{ \"errmsg\": \"试卷不存在。\" }', content_type='text/json')

        if if_exam == '1':
            TestPapers.objects.filter(paper_id=pid_obj, if_exam=True, weixin_open_id=me).delete()

        new_paper = TestPapers()
        new_paper.paper_id = pid_obj
        new_paper.if_exam = if_exam == '1'

        new_paper.weixin_open_id = me
        new_paper.date_time = datetime.datetime.now()
        new_paper.score = 0.0
        new_paper.done = False
        new_paper.save()

        pd_obj = json.loads(paper_detail)
        total_score = 0.0
        q_count = 0
        for (q_id, q_ans) in pd_obj.items():
            tq = TestQuestions()
            ques = Questions.objects.get(question_id=q_id)
            tq.question_id = ques
            tq.test_paper_id = new_paper
            tq.answers = q_ans.replace(',', '')
            q_count += 1
            tq.sn = q_count

            if q_ans.replace(',', '') == ques.question_right_answers:
                total_score += 1.0
                tq.score = 1.0
            else:
                tq.score = 0.0
            tq.save()

        total_score_100 = (total_score / q_count) * 100
        new_paper.score = total_score_100
        new_paper.done = True
        new_paper.save()

        return HttpResponse('{ \"errmsg\": \"OK\", \"score\": \"%f\", \"passing_score\": \"%f\", \"test_paper_id\": \"%s\" }' % (total_score_100, pid_obj.passing_score, new_paper.test_paper_id), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def handinExam(request):
    exam_paper_id = request.POST.get('exam_paper_id', None)
    paper_detail = request.POST.get('paper_detail', None)
    if not exam_paper_id or not paper_detail:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    me = Members.objects.get(weixin_open_id=woi, deleted=0, verified=1)
    if not me:
        return HttpResponse('{ \"errmsg\": \"该用户不存在。\" }', content_type='text/json')

    try:
        exam_obj = ExamPapers.objects.get(exam_paper_id=exam_paper_id)
        if not exam_obj:
            return HttpResponse('{ \"errmsg\": \"试卷不存在。\" }', content_type='text/json')
        
        ExamQuestions.objects.filter(exam_paper_id=exam_obj).delete()

        pd_obj = json.loads(paper_detail)
        total_score = 0.0
        q_count = 0
        for (q_id, q_ans) in pd_obj.items():
            tq = ExamQuestions()
            ques = Questions.objects.get(question_id=q_id)
            tq.question_id = ques
            tq.exam_paper_id = exam_obj
            tq.answers = q_ans.replace(',', '')
            q_count += 1
            tq.sn = q_count

            if q_ans.replace(',', '') == ques.question_right_answers:
                total_score += 1.0
                tq.score = 1.0
            else:
                tq.score = 0.0
            tq.save()

        total_score_100 = (total_score / q_count) * 100
        exam_obj.score = total_score_100
        exam_obj.done = True
        exam_obj.done_date = datetime.datetime.now()
        exam_obj.save()

        return HttpResponse('{ \"errmsg\": \"OK\", \"score\": \"%f\", \"passing_score\": \"%f\"}' % (total_score_100, exam_obj.passing_score), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

@csrf_exempt
def getUndoneExamCount(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
    try:
        count = ExamPapers.objects.filter(weixin_open_id=woi, done=False, avail_start__lte=datetime.datetime.now(), avail_end__gte=datetime.datetime.now()).count()
        return HttpResponse('{ \"count\": \"%d\" }' % (count,), content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e))
@csrf_exempt
def signin(request):
    woi = request.session.get('open_id', None)
    
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    try:
        log_count = 0
        if not SignInLog.objects.filter(
                date_time__gte=datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d 00:00:00'), '%Y-%m-%d %H:%M:%S'),
                date_time__lte=datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d 23:59:59'), '%Y-%m-%d %H:%M:%S'),
                weixin_open_id=woi).exists():
            sign_in_log = SignInLog.objects.get_or_create(weixin_open_id=woi)
            log = sign_in_log[0]
            log_count = (1 if log.count is None else log.count + 1)
            log.count = log_count
            log.date_time = datetime.datetime.now()
            log.save()
        else:
            log_count = SignInLog.objects.get(
                date_time__gte=datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d 00:00:00'), '%Y-%m-%d %H:%M:%S'),
                date_time__lte=datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d 23:59:59'), '%Y-%m-%d %H:%M:%S'),
                weixin_open_id=woi).count

        return HttpResponse('{ \"errmsg\": \"OK\", \"count\": \"%s\" }' % log_count, content_type='text/json')
    except Exception as e:
        return HttpResponse('{ \"errmsg\": \"%s\" }' % str(e), content_type='text/json')

#@csrf_exempt
#def openTestRedPacket(request):
#    woi = request.session.get('open_id', None)
#    score =  request.POST.get('score', 0.0)
#    test_paper_id = request.POST.get('test_paper_id', None)
#
#    if not woi:
#        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
#
#    if not test_paper_id or score is None:
#        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')
#
#    fullwork_rp = -1
#    fullmark_rp = -1
#
#    try:
#        if not TestPapers.objects.filter(test_paper_id=test_paper_id).exists():
#            return HttpResponse('{ \"errmsg\": \"练习不存在。\" }', content_type='text/json')
#        
#        if TestRedPackets.objects.filter(test_paper_id=test_paper_id, weixin_open_id=woi).exists():
#            return HttpResponse('{ \"errmsg\": \"您已经获得过本次练习的红包。\" }', content_type='text/json')
#
#        tp = TestPapers.objects.get(test_paper_id=test_paper_id)
#        
#        if SignInLog.objects.filter(weixin_open_id=woi).exists():
#            sil = SignInLog.objects.get(weixin_open_id=woi)
#
#        if not RedPacketType.objects.filter(pt_id=1).exists():
#            return HttpResponse('{ \"errmsg\": \"没有此类红包。\" }', content_type='text/json')
#
#        prob = 0.5
#        fullwork_rp = get_random_rp(prob)
#        if sil.count >= 7 and tp.score >= 60:
#            if fullwork_rp > 0:
#                rpt = RedPacketType.objects.get(pt_id=1)
#                trp = TestRedPackets()
#                trp.weixin_open_id = woi
#                trp.amount = '%.2f' % (0 if fullwork_rp == -1 else fullwork_rp)
#                trp.date_time = datetime.datetime.now()
#                trp.test_paper_id = tp
#                trp.red_packet_type_id = rpt
#                trp.save()
#        else:
#            fullwork_rp = 0.00
#
#        if not RedPacketType.objects.filter(pt_id=2).exists():
#            return HttpResponse('{ \"errmsg\": \"没有此类红包。\" }', content_type='text/json')
#        
#        fullmark_rp = get_random_rp(prob)
#        if fullmark_rp > 0:
#            rpt = RedPacketType.objects.get(pt_id=2)
#            trp = TestRedPackets()
#            trp.weixin_open_id = woi
#            trp.amount = '%.2f' % (0 if fullmark_rp == -1 else fullmark_rp)
#            trp.date_time = datetime.datetime.now()
#            trp.test_paper_id = tp
#            trp.red_packet_type_id = rpt
#            trp.save()
#        
#        fullwork_rp = '%.2f' % fullwork_rp
#        fullmark_rp = '%.2f' % fullmark_rp
#
#        return HttpResponse('{ \"fwp\": \"%s\", \"fmp\": \"%s\" }' % (fullwork_rp, fullmark_rp), content_type='text/json')
#    except Exception as e:
#        exc_type, exc_obj, exc_tb = sys.exc_info()
#        return HttpResponse('{ \"errmsg\": \"%s行号：%s\"  }' % (str(e), exc_tb.tb_lineno), content_type='text/json')
#
#def get_random_rp(big_rp_probality):
#    rand_float = random.random()
#    if rand_float < 0.5:
#        rp = random.uniform(5, 10)
#    else:
#        rp = random.uniform(0, 5)
#
#    return rp
@csrf_exempt
def openTestRedPacket(request):
    woi = request.session.get('open_id', None)
    score =  request.POST.get('score', 0.0)
    test_paper_id = request.POST.get('test_paper_id', None)

    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    if not test_paper_id or score is None:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    fullwork_rp = -1
    fullmark_rp = -1
    try:
        if not TestPapers.objects.filter(test_paper_id=test_paper_id).exists():
            return HttpResponse('{ \"errmsg\": \"练习不存在。\" }', content_type='text/json')
        
        if TestRedPackets.objects.filter(test_paper_id=test_paper_id, weixin_open_id=woi).exists():
            return HttpResponse('{ \"errmsg\": \"您已经获得过本次练习的红包。\" }', content_type='text/json')

        tp = TestPapers.objects.get(test_paper_id=test_paper_id)

        fw_req_id = str(uuid.uuid1())
        
        if SignInLog.objects.filter(weixin_open_id=woi).exists():
            sil = SignInLog.objects.get(weixin_open_id=woi)

            resp = requests.post('https://rp.jingjingjing.wang/jsonrpc', 
                    data=json.dumps({
                        'jsonrpc': '2.0',
                        'method': 'checkFullWork', 
                        'params': [woi, str(sil.count), str(score)],
                        'id': fw_req_id
                    }),
                    headers={
                        'Content-Type': 'application/json'
                    })

            resp_obj = resp.json()
            if 'error' in resp_obj:
                return HttpResponse('{ \"errmsg\": \"(checkFullWork)%s: %s\" }' % (resp_obj['error']['code'], resp_obj['error']['message']))
            else:
                fullwork_rp = resp_obj['result']

            if not RedPacketType.objects.filter(pt_id=1).exists():
                return HttpResponse('{ \"errmsg\": \"没有此类红包。\" }', content_type='text/json')
            
            f_fullwork_rp = float(fullwork_rp)
            if f_fullwork_rp > 0:
                rpt = RedPacketType.objects.get(pt_id=1)
                trp = TestRedPackets()
                trp.weixin_open_id = woi
                trp.amount = (0 if f_fullwork_rp == -1 else f_fullwork_rp)
                trp.date_time = datetime.datetime.now()
                trp.test_paper_id = tp
                trp.red_packet_type_id = rpt
                trp.save()

        fm_req_id = str(uuid.uuid1())

        resp = requests.post('https://rp.jingjingjing.wang/jsonrpc', 
                data=json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'checkFullMark', 
                    'params': {
                        'openid': woi,
                        'exam': 'practice',
                        'mark': str(score)
                    },
                    'id': fm_req_id
                }),
                headers={
                    'Content-Type': 'application/json'
                })

        resp_obj = resp.json()
        if 'error' in resp_obj:
            return HttpResponse('{ \"errmsg\": \"(checkFullMark)%s: %s\" }' % (resp_obj['error']['code'], resp_obj['error']['message']))
        else:
            fullmark_rp = resp_obj['result']

        if not RedPacketType.objects.filter(pt_id=2).exists():
            return HttpResponse('{ \"errmsg\": \"没有此类红包。\" }', content_type='text/json')
        
        f_fullmark_rp = float(fullmark_rp)
        if f_fullmark_rp > 0:
            rpt = RedPacketType.objects.get(pt_id=2)
            trp = TestRedPackets()
            trp.weixin_open_id = woi
            trp.amount = (0 if f_fullmark_rp == -1 else f_fullmark_rp)
            trp.date_time = datetime.datetime.now()
            trp.test_paper_id = tp
            trp.red_packet_type_id = rpt
            trp.save()

        return HttpResponse('{ \"fwp\": \"%s\", \"fmp\": \"%s\" }' % (fullwork_rp, fullmark_rp), content_type='text/json')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\"  }' % (str(e), exc_tb.tb_lineno), content_type='text/json')

@csrf_exempt
def getCurrentAccumulatePoints(request):
    woi = request.session.get('open_id', None)
    tp_id = request.POST.get('test_paper_id', None)
    
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
    
    if tp_id is None:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    try:
        if tp_id != 0 and not TestPapers.objects.filter(test_paper_id=tp_id).exists():
            return HttpResponse('{ \"errmsg\": \"练习不存在。\" }', content_type='text/json')

        cur_acc_points = AccumulatePointsLog.objects.select_related().filter(weixin_open_id=woi, test_paper_id__test_paper_id=int(tp_id)).aggregate(points_sum=Sum('points'))['points_sum']
        if AccumulatePoints.objects.filter(weixin_open_id=woi).exists():
            total_acc_points = AccumulatePoints.objects.get(weixin_open_id=woi).points
        else:
            total_acc_points = 0.00

        return HttpResponse('{ \"cur_acc_points\": \"%s\", \"accumulate_points\": \"%s\" }' % (str(cur_acc_points), str(total_acc_points)), content_type='text/json')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\" }' % (str(e), exc_tb.tb_lineno), content_type='text/json')
@csrf_exempt
def getRPandAP(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
    
    try:
        now = datetime.datetime.now()
        this_month_start = datetime.datetime(now.year, now.month, 1, 0, 0, 0)
        this_month_end = datetime.datetime(now.year, now.month + 1, 1, 23, 59, 59) - datetime.timedelta(days=1)

        rp = TestRedPackets.objects.filter(weixin_open_id=woi, date_time__gte=this_month_start, date_time__lte=this_month_end).order_by('-date_time')
        rp_amount = rp.aggregate(amount=Sum('amount'))['amount'] 
        rp_amount = (0.0 if rp_amount is None else '%.2f' % rp_amount)

        rp_detail = list()
        
        for r in rp:
            rp_detail.append({
                'rp_id': r.rp_id,
                'count': r.amount,
                'paper_name': r.test_paper_id.paper_id.paper_name,
                'date_time': r.date_time.strftime('%Y年%m月%d %H:%M:%S'),
                'type_name': r.red_packet_type_id.pt_name
            })

        ap_amount = AccumulatePoints.objects.get_or_create(weixin_open_id=woi)
        ap_amount = ap_amount[0].points

        ap = AccumulatePointsLog.objects.filter(weixin_open_id=woi, date_time__gte=this_month_start, date_time__lte=this_month_end).order_by('-date_time')
        ap_detail = list()

        for a in ap:
            ap_detail.append({
                'ap_id': a.ap_id,
                'count': a.points,
                'paper_name': ('' if not hasattr(a, 'test_paper_id') or a.test_paper_id is None else a.test_paper_id.paper_id.paper_name),
                'type_name': a.ap_type_id.type_name,
                'date_time': a.date_time.strftime('%Y年%m月%d日 %H:%M:%S')
            })

        return HttpResponse('{ \"rp_amount\": \"%s\", \"rp_detail\": %s, \"ap_amount\": \"%s\", \"ap_detail\": %s }' % (rp_amount, json.dumps(rp_detail), ap_amount, json.dumps(ap_detail)), content_type='text/json')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\" }' % (str(e), exc_tb.tb_lineno), content_type='text/json')
@csrf_exempt
def getMyWrongList(request):
    woi = request.session.get('open_id', None)
    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')

    date_start = request.POST.get('date_start', None)
    date_end = request.POST.get('date_end', None)

    if not date_start or not date_end:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')
    
    try:
        ret = list()
        wrongs = V_Wrongs.objects.filter(weixin_open_id=woi,
                date_time__gte=datetime.datetime.strptime(date_start + ' 00:00:00', '%Y-%m-%d %H:%M:%S'),
                date_time__lte=datetime.datetime.strptime(date_end + ' 23:59:59', '%Y-%m-%d %H:%M:%S')).order_by('-wrong_count', '-date_time', 'question_id')
        
        for w in wrongs:
            ret.append({
                'question_id': w.question_id,
                'test_question_id': w.test_question_id,
                'question_title': w.question_title,
                'question_type': question_type_map[str(w.question_type)],
                'question_answer_texts': w.question_answer_texts,
                'question_right_answers': w.question_right_answers,
                'wrong_count': w.wrong_count,
                'date_time': w.date_time.strftime('%Y年%m月%d日 %H:%M:%S')
            })
        return HttpResponse(json.dumps(ret), content_type='text/json')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\" }' % (str(e), exc_tb.tb_lineno), content_type='text/json')

@csrf_exempt
def getWrongAnswerDetail(request):
    woi = request.session.get('open_id', None)
    q_id = request.POST.get('question_id', None)
    date_start = request.POST.get('date_start', None)
    date_end = request.POST.get('date_end', None)

    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
    if not q_id or not date_start or not date_end:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    try:
        wrong_answers = TestQuestions.objects.select_related().filter(test_paper_id__weixin_open_id=woi,
                test_paper_id__date_time__gte=datetime.datetime.strptime(date_start+' 00:00:00', '%Y-%m-%d %H:%M:%S'),
                test_paper_id__date_time__lte=datetime.datetime.strptime(date_end+' 23:59:59', '%Y-%m-%d %H:%M:%S'),
                question_id__question_id=int(q_id)).values_list('answers', flat=True)
        
        wn = WrongNote.objects.select_related().filter(weixin_open_id=woi, question_id__question_id=q_id)
        if not wn.exists():
            wn = ''
        else:
            wn = WrongNote.objects.select_related().filter(weixin_open_id=woi, question_id__question_id=q_id).first()
            wn = wn.note

        ret = { 'wrong_answers': list(wrong_answers), 'wrong_note': wn }

        return HttpResponse(json.dumps(ret), content_type='text/json')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\" }' % (str(e), exc_tb.tb_lineno), content_type='text/json')

@csrf_exempt
def saveWrongNote(request):
    woi = request.session.get('open_id', None)
    q_id = request.POST.get('question_id', None)
    note = request.POST.get('note', '')

    if not woi:
        return HttpResponse('{ \"errmsg\": \"登录信息丢失。\" }', content_type='text/json')
    if not q_id:
        return HttpResponse('{ \"errmsg\": \"请求异常。\" }', content_type='text/json')

    try:
        if not Questions.objects.filter(question_id=q_id).exists():
            return HttpResponse('{ \"errmsg\": \"找不到此试题。\" }', content_type='text/json')

        q = Questions.objects.get(question_id=q_id)
        wn = WrongNote.objects.get_or_create(question_id=q, weixin_open_id=woi)
        wn = wn[0]
        wn.question_id = q
        wn.weixin_open_id = woi
        wn.note = note
        wn.save()
        return HttpResponse('OK')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        return HttpResponse('{ \"errmsg\": \"%s行号：%s\" }' % (str(e), exc_tb.tb_lineno), content_type='text/json')

def safe_new_datetime(d):
    kw = [d.year, d.month, d.day]
    if isinstance(d, datetime.datetime):
        kw.extend([d.hour, d.minute, d.second, d.microsecond, d.tzinfo])
    return datetime.datetime(*kw)
                        
def safe_new_date(d):
    return datetime.date(d.year, d.month, d.day)

class DateTimeJSONEncoder(json.JSONEncoder):
    DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%H:%M:%S'

    def default(self, o):
        if isinstance(o, datetime.datetime):
            d = safe_new_datetime(o)
            return d.strftime('%s %s' % (self.DATE_FORMAT, self.TIME_FORMAT))
        elif isinstance(o, datetime.date):
            d = safe_new_date(o)
            return d.strftime(self.DATE_FORMAT)
        elif isinstance(o, datetime.time):
            return o.strftime(self.TIME_FORMAT)
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(DateTimeJSONEncoder, self).default(o)

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row)) for row in cursor.fetchall()
    ]

def debugLog(mes):
    log = logging.getLogger('nc_exam_file_debug_logger')
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s][第%(lineno)s行] - %(message)s');
    fh = logging.FileHandler('/home/carzpurzkey/projects/nc_exam/nc_exam/main/log.log', mode='a', encoding='utf-8')
    fh.setFormatter(formatter)
    log.addHandler(fh)
    log.debug(mes)
