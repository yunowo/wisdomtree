import logging
import json
from datetime import datetime, timedelta
from getpass import getpass
import uuid
import requests
from Cryptodome.PublicKey import RSA

import utils

NONE, SIGN, TICKET = 0, 1, 2

SERVER = 'https://appstudentapi.zhihuishu.com'
SSL_VERIFY = True
TAKE_EXAMS = True
SKIP_FINAL_EXAM = False
EXAM_AUTO_SUBMIT = True


def post(head, url, data, raw=False):
    timestamp = str(int(datetime.now().timestamp() * 1000))
    s.headers.update({'Timestamp': timestamp})
    if head == SIGN:
        s.headers.update({'App-Signature': utils.md5_encrypt(app_key + timestamp + secret)})
    elif head == TICKET:
        s.headers.update({'App-Ticket': ticket})
    r = s.post(SERVER + url, data=data, verify=SSL_VERIFY)
    if raw is True:
        return r.text
    return r.json()['rt']


def login():
    account = input('Account(Phone):')
    password = getpass(prompt='Password:')
    assert account or password

    p = {'appkey': app_key}
    global ticket
    ticket = post(NONE, '/api/ticket', p)

    p = {'platform': 'android', 'm': account, 'appkey': app_key, 'p': password, 'client': 'student',
         'version': '2.8.9'}
    d = post(TICKET, '/api/login', p)
    u = d['userId']
    se = d['secret']

    s.headers.clear()
    p = {'type': 3, 'userId': u, 'secretStr': utils.rsa_encrypt(rsa_key, u), 'versionKey': 1}
    d = post(SIGN, '/appstudent/student/user/getUserInfoAndAuthentication', p)
    ai = json.loads(utils.rsa_decrypt(rsa_key, d['authInfo']))
    ui = json.loads(utils.rsa_decrypt(rsa_key, d['userInfo']))
    logger.info(ai)
    logger.info(ui)
    n = ui['realName']
    logger.info(f'{u} {n}')
    with open('userinfo.py', 'w+', encoding='utf-8') as f:
        f.writelines(f'USER = {u}\n')
        f.writelines(f'NAME = "{n}"\n')
        f.writelines(f'SECRET = "{se}"')
    logger.info('Login OK.')
    return u, n, se


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
    secret = ''
    ticket = ''

    try:
        import userinfo

        user = userinfo.USER
        name = userinfo.NAME
        secret = userinfo.SECRET
        if input(f'Current user:{user} {name}:[y/n]') != 'y':
            user, name, secret = login()
    except:
        user, name, secret = login()

    SERVER += '/appstudent'
    p = {'userId': user}
    d = post(SIGN, '/student/tutorial/getStudyingCourses', p)
    course_id, recruit_id, link_course_id = 0, 0, 0
    if d is None:
        logger.info('No studying courses.')
        exit()
    for course in d:
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
        p = {'deviceId': app_key, 'userId': user, 'versionKey': 1}
        rt = post(SIGN, '/student/tutorial/getSaveLearningRecordToken', p)
        token = utils.rsa_decrypt(rsa_key, rt)
        video_time = dic['videoSec']
        chapter_id = chapter_id or dic['chapterId']
        j = {'lessonId': lesson_id, 'learnTime': str(timedelta(seconds=video_time)), 'userId': user,
             'personalCourseId': link_course_id, 'recruitId': recruit_id, 'chapterId': chapter_id, 'sourseType': 3,
             'playTimes': video_time, 'videoId': dic['videoId'], 'token': token, 'deviceId': app_key}
        if lesson_id is None:
            j['lessonId'] = dic['id']
        else:
            j['lessonVideoId'] = dic['id']
        json_str = json.dumps(j, sort_keys=True, separators=(',', ':'))
        p = {'jsonStr': json_str, 'secretStr': utils.rsa_encrypt(rsa_key, json_str), 'versionKey': 1}
        rt = post(SIGN, '/student/tutorial/saveLearningRecordByToken', p)
        logger.info(dic['name'] + rt)


    p = {'recruitId': recruit_id, 'courseId': course_id, 'userId': user}
    chapter_list = post(SIGN, '/appserver/student/getCourseInfo', p)['chapterList']
    for chapter in chapter_list:
        for lesson in chapter['lessonList']:
            if lesson['sectionList'] is not None:
                for section in lesson['sectionList']:
                    save_record(section, lesson['chapterId'], lesson['id'])
            else:
                save_record(lesson, None, None)

    logger.info('Videos done.')

    if TAKE_EXAMS is False:
        exit()

    p = {'mobileType': 2, 'recruitId': recruit_id, 'courseId': course_id, 'page': 1, 'userId': user, 'examType': 1,
         'schoolId': -1, 'pageSize': 20}  # examType=2 is for finished exams
    exam_list = post(SIGN, '/appserver/exam/findAllExamInfo', p)['stuExamDtoList']
    for exam in exam_list:
        logger.info(exam['examInfoDto']['name'])
        exam_type = exam['examInfoDto']['type']
        if exam_type == 2:  # Final exams
            if SKIP_FINAL_EXAM is True:
                logger.info('Skipped final exam.')
                continue
        exam_id = exam['examInfoDto']['examId']
        student_exam_id = exam['studentExamInfoDto']['id']
        question_ids = []

        p = {'userId': user}
        rt = post(SIGN, '/student/exam/canIntoExam', p)
        if rt != 1:
            logger.info('Cannot into exam.')
            continue

        p = {'recruitId': recruit_id, 'examId': exam_id, 'isSubmit': 0, 'studentExamId': student_exam_id,
             'type': exam_type, 'userId': user}
        ids = post(SIGN, '/student/exam/examQuestionIdListByCache', p)['examList']
        p.pop('isSubmit')
        p.pop('type')
        for exam_question in ids:
            question_ids.append(str(exam_question['questionId']))
            p['questionIds'] = question_ids

        questions = post(SIGN, '/student/exam/questionInfos', p)
        for question_id in question_ids:
            question = questions[question_id]
            logger.info(question['firstname'])
            if question['questionTypeName'] == '多选题' or '单选题':
                answer = question['realAnswer'].split(',')
            else:
                EXAM_AUTO_SUBMIT = False
                continue

            pa = [{'deviceType': '1', 'examId': str(exam_id), 'userId': str(user), 'stuExamId': str(student_exam_id),
                   'questionId': str(question_id), 'recruitId': str(recruit_id), 'answerIds': answer, 'dataIds': []}]
            json_str = json.dumps(pa, separators=(',', ':'))
            pb = {'mobileType': 2, 'jsonStr': json_str,
                  'secretStr': utils.rsa_encrypt(rsa_key, json_str),
                  'versionKey': 1}
            rt = post(SIGN, '/student/exam/saveExamAnswer', pb)
            logger.info(rt[0]['messages'])
        if not EXAM_AUTO_SUBMIT:
            continue

        pa = {'deviceType': '1', 'userId': str(user), 'stuExamId': str(student_exam_id), 'recruitId': recruit_id,
              'examId': str(exam_id), 'questionIds': question_ids, 'remainingTime': '0',
              'achieveCount': str(question_ids.__len__())}
        json_str = json.dumps(pa, separators=(',', ':'))
        pb = {'mobileType': 2, 'recruitId': recruit_id, 'examId': str(exam_id), 'userId': user, 'jsonStr': json_str,
              'secretStr': utils.rsa_encrypt(rsa_key, json_str), 'type': exam_type, 'versionKey': 1}
        raw = post(SIGN, '/student/exam/submitExamInfo', pb, raw=True)
        rt = json.loads(raw.replace('"{', '{').replace('}"', '}').replace('\\', ''))['rt']
        logger.info(f'{rt["messages"]} Score: {rt["errorInfo"]["score"]}')

    logger.info('Exams done.')
