import logging
import json
from datetime import datetime, timedelta
from getpass import getpass
import uuid
import requests
from Cryptodome.PublicKey import RSA

import utils

SERVER = 'https://appstudentapi.zhihuishu.com'
SSL_VERIFY = True
TAKE_EXAMS = True
SKIP_FINAL_EXAM = False
EXAM_AUTO_SUBMIT = True

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO)
    logger = logging.getLogger()
    logger.info('I love studying! Study makes me happy!')

    rsa_key = RSA.import_key(open('key.pem', 'r').read())
    app_key = utils.md5_encrypt(str(uuid.uuid4()).replace('-', ''))

    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.1; Nexus 5X Build/NOF27B',
        'Accept-Encoding': 'gzip',
        'App-Key': app_key})
    s.cookies.update({'Z_LOCALE': '2'})
    secret = ''


    def add_headers_ticket(t):
        timestamp = str(int(datetime.now().timestamp() * 1000))
        s.headers.update({
            'Timestamp': timestamp,
            'App-Ticket': t
        })


    def add_headers_signature():
        timestamp = str(int(datetime.now().timestamp() * 1000))
        s.headers.update({
            'Timestamp': timestamp,
            'App-Signature': utils.md5_encrypt(app_key + timestamp + secret)
        })


    def add_headers_timestamp_only():
        timestamp = str(int(datetime.now().timestamp() * 1000))
        s.headers.update({
            'Timestamp': timestamp,
        })


    def login():
        account = input('Account(Phone):')
        password = getpass(prompt='Password:')
        assert account or password

        add_headers_timestamp_only()
        p = {'appkey': app_key}
        r = s.post(SERVER + '/api/ticket', data=p, verify=SSL_VERIFY)
        ticket = r.json()['rt']

        add_headers_ticket(ticket)
        p = {'platform': 'android', 'm': account, 'appkey': app_key, 'p': password, 'client': 'student',
             'version': '2.8.8'}
        r = s.post(SERVER + '/api/login', data=p, verify=SSL_VERIFY)
        d = r.json()['rt']
        u = d['userId']
        se = d['secret']

        s.headers.clear()
        timestamp = str(int(datetime.now().timestamp() * 1000))
        s.headers.update({
            'Timestamp': timestamp,
            'App-Signature': utils.md5_encrypt(app_key + timestamp + se)
        })
        # p = {'type': 1, 'userId': u, 'secretStr': utils.md5_encrypt(se), 'versionKey': 1}
        # r = s.post(SERVER + '/appstudent/student/user/getUserInfoAndAuthentication', data=p, verify=SSL_VERIFY)
        # d = r.json()['rt']
        # ai = d['authInfo']
        # ui = d['userInfo']
        # logger.info(utils.rsa_decrypt(rsa_key, ai))
        # logger.info(utils.rsa_decrypt(rsa_key, ui))
        n = 'Your name'
        logger.info('{} {}'.format(u, n))
        with open('userinfo.py', 'w+', encoding='utf-8') as f:
            f.writelines('USER = {}\n'.format(u))
            f.writelines('NAME = "{}"\n'.format(n))
            f.writelines('SECRET = "{}"'.format(se))
        logger.info('Login OK.')
        return u, n, se


    try:
        import userinfo

        user = userinfo.USER
        name = userinfo.NAME
        secret = userinfo.SECRET
        if input('Current user:{} {}:[y/n]'.format(user, name)) != 'y':
            user, name, secret = login()
    except:
        user, name, secret = login()

    SERVER += '/appstudent'
    add_headers_signature()
    p = {'userId': user}
    r = s.post(SERVER + '/student/tutorial/getStudyingCourses', data=p, verify=SSL_VERIFY)
    course_id, recruit_id, link_course_id = 0, 0, 0
    if r.json()['rt'] is None:
        logger.info('No studying courses.')
        exit()
    for course in r.json()['rt']:
        if input(course['courseName'] + ':[y/n]') == 'y':
            course_id = course['courseId']
            recruit_id = course['recruitId']
            link_course_id = course['linkCourseId']
            break
    if course_id == 0:
        exit()


    def save_record(dic, chapter_id, lesson_id):
        if dic['studiedLessonDto'] is not None and dic['studiedLessonDto']['watchState'] == 1:
            return
        add_headers_signature()
        p = {'deviceId': app_key, 'userId': user, 'versionKey': 1}
        r = s.post(SERVER + '/student/tutorial/getSaveLearningRecordToken', data=p, verify=SSL_VERIFY)
        token = utils.rsa_decrypt(rsa_key, r.json()['rt'])
        video_time = dic['videoSec']
        chapter_id = chapter_id or dic['chapterId']
        j = {'lessonId': lesson_id, 'learnTime': str(timedelta(seconds=video_time)), 'userId': user,
             'personalCourseId': link_course_id, 'recruitId': recruit_id, 'chapterId': chapter_id, 'sourseType': 3,
             'playTimes': video_time, 'videoId': dic['videoId'], 'token': token, 'deviceId': app_key}
        if lesson_id is None:
            j['lessonId'] = dic['id']
        else:
            j['lessonVideoId'] = dic['id']
        add_headers_signature()
        jsonstr = json.dumps(j, sort_keys=True, separators=(',', ':'))
        p = {'jsonStr': jsonstr, 'secretStr': utils.rsa_encrypt(rsa_key, jsonstr.encode('utf-8')), 'versionKey': 1}
        r = s.post(SERVER + '/student/tutorial/saveLearningRecordByToken', data=p, verify=SSL_VERIFY)
        logger.info(dic['name'] + r.json()['rt'])


    add_headers_signature()
    p = {'recruitId': recruit_id, 'courseId': course_id, 'userId': user}
    r = s.post(SERVER + '/appserver/student/getCourseInfo', data=p, verify=SSL_VERIFY)
    for chapter in r.json()['rt']['chapterList']:
        for lesson in chapter['lessonList']:
            if lesson['sectionList'] is not None:
                for section in lesson['sectionList']:
                    save_record(section, lesson['chapterId'], lesson['id'])
            else:
                save_record(lesson, None, None)

    logger.info('Videos done.')

    if TAKE_EXAMS is False:
        exit()

    add_headers_signature()
    p = {'mobileType': 2, 'recruitId': recruit_id, 'courseId': course_id, 'page': 1, 'userId': user, 'examType': 1,
         'schoolId': -1, 'pageSize': 20}  # examType=2 is for finished exams
    r = s.post(SERVER + '/appserver/exam/findAllExamInfo', data=p, verify=SSL_VERIFY)
    for exam in r.json()['rt']['stuExamDtoList']:
        logger.info(exam['examInfoDto']['name'])
        exam_type = exam['examInfoDto']['type']
        if exam_type == 2:  # Final exams
            if SKIP_FINAL_EXAM is True:
                logger.info('Skipped final exam.')
                continue
        exam_id = exam['examInfoDto']['examId']
        student_exam_id = exam['studentExamInfoDto']['id']
        question_ids = []

        add_headers_signature()
        p = {'recruitId': recruit_id, 'examId': exam_id, 'isSubmit': 0, 'studentExamId': student_exam_id,
             'type': exam_type, 'userId': user}
        r = s.post(SERVER + '/student/exam/examQuestionIdListByCache', data=p, verify=SSL_VERIFY)
        p.pop('isSubmit')
        p.pop('type')
        for question in r.json()['rt']['examList']:
            question_ids.append(str(question['questionId']))
            p['questionIds'] = question_ids

        add_headers_signature()
        r = s.post(SERVER + '/student/exam/questionInfos', data=p, verify=SSL_VERIFY)
        d = r.json()['rt']
        for question_id in question_ids:
            question = d[question_id]
            logger.info(question['firstname'])
            if question['questionTypeName'] == '多选题' or '单选题':
                answer = question['realAnswer'].split(',')
            else:
                EXAM_AUTO_SUBMIT = False
                continue

            add_headers_signature()
            pa = [{'deviceType': '1', 'examId': str(exam_id), 'userId': str(user), 'stuExamId': str(student_exam_id),
                   'questionId': str(question_id), 'recruitId': str(recruit_id), 'answerIds': answer, 'dataIds': []}]
            json_str = json.dumps(pa, separators=(',', ':'))
            pb = {'mobileType': 2, 'jsonStr': json_str,
                  'secretStr': utils.rsa_encrypt(rsa_key, json_str.encode('utf-8')),
                  'versionKey': 1}
            r = s.post(SERVER + '/student/exam/saveExamAnswer', data=pb, verify=SSL_VERIFY)
            logger.info(r.json()['rt'][0]['messages'])
        if not EXAM_AUTO_SUBMIT:
            continue

        add_headers_signature()
        pa = {'deviceType': '1', 'userId': str(user), 'stuExamId': str(student_exam_id), 'recruitId': recruit_id,
              'examId': str(exam_id), 'questionIds': question_ids, 'remainingTime': '0',
              'achieveCount': str(question_ids.__len__())}
        json_str = json.dumps(pa, separators=(',', ':'))
        pb = {'mobileType': 2, 'recruitId': recruit_id, 'examId': str(exam_id), 'userId': user, 'jsonStr': json_str,
              'secretStr': utils.rsa_encrypt(rsa_key, json_str.encode('utf-8')), 'type': exam_type, 'versionKey': 1}
        r = s.post(SERVER + '/student/exam/submitExamInfo', data=pb, verify=SSL_VERIFY)
        d = json.loads(r.text.replace('"{', '{').replace('}"', '}').replace('\\', ''))['rt']
        logger.info(d['messages'] + ' Score: ' + d['errorInfo']['score'])

    logger.info('Exams done.')
