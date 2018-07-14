import itertools
import logging
import json
import random
import time
from datetime import datetime, timedelta
from getpass import getpass
import uuid
import requests
from Cryptodome.PublicKey import RSA

import utils

SERVER = 'https://appstudent.zhihuishu.com/appstudent'
SSL_VERIFY = True
TAKE_EXAMS = False
SKIP_FINAL_EXAM = False
EXAM_AUTO_SUBMIT = False


def post(url, data, raw=False, sleep=True):
    r = s.post(SERVER + url, data=data, verify=SSL_VERIFY)
    if sleep:
        time.sleep(0.5 + random.random())
    if raw is True:
        return r.text
    j = r.json()
    if 'rt' in j:
        return j['rt']
    else:
        logger.error(j['msg'])
        raise ValueError(j['msg'])


def login():
    account = input('Account(Phone):')
    password = getpass(prompt='Password:')
    assert account or password

    p = {'account': account, 'password': password, 'areaCode': '86', 'appVersion': '4.0.6', 'clientType': '1',
         'imei': uuid.uuid4().hex}
    pp = {'paramJsonStr': utils.rsa_encrypt_public(public_key, json.dumps(p, separators=(',', ':'))),
          'timeNote': '1515340800'}
    d = post('/newuser/userLoginByAccount', pp, sleep=False)
    u = d['userId']
    uu = d['userUUID']

    p = {'type': 3, 'userUUID': uu, 'secretStr': utils.rsa_encrypt(rsa_key, str(u)), 'versionKey': 1}
    d = post('/student/user/getUserInfoAndAuthenticationByUUID', p, sleep=False)
    ai = json.loads(utils.rsa_decrypt(rsa_key, d['authInfo']))
    ui = json.loads(utils.rsa_decrypt(rsa_key, d['userInfo']))
    logger.info(ai)
    logger.info(ui)
    n = ui['realName']
    logger.info(f'{u} {uu} {n}')
    with open('userinfo.py', 'w+', encoding='utf-8') as f:
        f.writelines(f'USER = {u}\n')
        f.writelines(f'UUID = "{uu}"\n')
        f.writelines(f'NAME = "{n}"\n')
    logger.info('Login OK.')
    return u, uu, n


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO)
    logger = logging.getLogger()
    logger.info('I love studying! Study makes me happy!')

    rsa_key = RSA.import_key(open('key.pem', 'r').read())
    public_key = RSA.import_key(open('public.pem', 'r').read())
    yzm_key = RSA.import_key(open('yzm.pem', 'r').read())
    app_key = utils.md5_digest(str(uuid.uuid4()).replace('-', ''))

    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 8.1.0; Pixel 2 XL Build/OPM1.171019.021)',
        'Accept-Encoding': 'gzip'})

    try:
        import userinfo

        user = userinfo.USER
        uu = userinfo.UUID
        name = userinfo.NAME
        if input(f'Current user:{user} {name}:[y/n]') != 'y':
            user, uu, name = login()
    except:
        user, uu, name = login()

    p = {'userId': user, 'page': 1, 'pageSize': 500}
    d = post('/student/tutorial/getStudyingCourseList', p, sleep=False)
    course_id, recruit_id, link_course_id = 0, 0, 0
    if d is None:
        logger.info('No studying courses.')
        exit()
    for course in d:
        if input(f'{course["courseName"]} {course["className"]}:[y/n]') == 'y':
            course_id = course['courseId']
            recruit_id = course['recruitId']
            link_course_id = course['linkCourseId']
            break
    if course_id == 0:
        exit()

    p = {'deviceId': app_key, 'uuid': uu, 'timeNote': '1515340800'}
    rt = post('/student/tutorial/getSaveStudyRecordToken', p)
    token = utils.rsa_decrypt_public(public_key, rt)


    def save_record(dic, lesson, is_section):
        if studied is not None and f'L{dic["id"]}' in studied and studied[f'L{dic["id"]}']['watchState'] == 1:
            return
        video_time = dic['videoSec']
        j = {'lessonId': lesson['id'], 'learnTime': str(timedelta(seconds=video_time)), 'userId': user,
             'personalCourseId': link_course_id, 'recruitId': recruit_id, 'chapterId': lesson['chapterId'],
             'sourseType': 3, 'playTimes': video_time, 'videoId': dic['videoId'], 'token': token, 'deviceId': app_key}
        if is_section:
            j['lessonVideoId'] = dic['id']
        json_str = json.dumps(j, sort_keys=True, separators=(',', ':'))
        p = {'jsonStr': json_str, 'secretStr': utils.rsa_encrypt(yzm_key, json_str), 'versionKey': 2}
        rt = post('/student/tutorial/saveLearningRecordByToken', p)
        logger.info(dic['name'] + rt)


    p = {'recruitId': recruit_id, 'courseId': course_id, 'userId': user}
    chapter_list = post('/courseStudy/course/getChaptersInfoOnly', p)['chapterList']
    studied = post('/appserver/student/queryStudiedLessonsNew', p)['studiedInfos']
    for chapter in chapter_list:
        for lesson in chapter['lessonList']:
            if lesson['sectionList'] is not None:
                for section in lesson['sectionList']:
                    save_record(section, lesson, True)
            else:
                save_record(lesson, lesson, False)

    logger.info('Videos done.')

    if TAKE_EXAMS is False:
        exit()

    p = {'mobileType': 2, 'recruitId': recruit_id, 'courseId': course_id, 'page': 1, 'userId': user, 'examType': 1,
         'pageSize': 20}  # examType=2 is for finished exams
    exam_list = post('/appserver/exam/findAllExamInfo', p)['stuExamDtoList']
    for exam in exam_list:
        logger.info(exam['examInfoDto']['name'])
        exam_type = exam['examInfoDto']['type']
        if exam_type == 2:  # Final exams
            if SKIP_FINAL_EXAM is True:
                logger.info('Skipped final exam.')
                continue
        begin_date = datetime.strptime(exam['studentExamInfoDto']['startTime'], '%Y-%m-%d %H:%M:%S')
        if datetime.today() < begin_date:
            logger.info('Exam not yet started.')
            continue

        exam_id = exam['examInfoDto']['examId']
        student_exam_id = exam['studentExamInfoDto']['id']
        question_ids = []

        p = {'recruitId': recruit_id, 'examId': exam_id, 'isSubmit': 0, 'studentExamId': student_exam_id,
             'type': exam_type, 'userId': user}
        ids = post('/student/exam/getExamQuestionIdFromTeacher', p)
        p.pop('isSubmit')
        p.pop('type')
        for exam_question in ids:
            question_ids.append(str(exam_question['questionId']))
            p['questionIds'] = f'[{",".join(question_ids)}]'

        questions = post('/student/exam/getQuestionDetailInfoFromTeacher', p)
        undone_question_ids = question_ids[:]
        for question_id in question_ids:
            question = questions[question_id]
            if question['questionTypeName'] == '问答题':
                undone_question_ids.remove(question_id)
                EXAM_AUTO_SUBMIT = False
                continue
            options = list(map(lambda o: o['optionid'], question['optionList']))
            if question['questionTypeName'] == '单选题' or question['questionTypeName'] == '判断题':
                question['possibleAnswers'] = options
            elif question['questionTypeName'] == '多选题':
                combinations = []
                for r in range(1, len(options) + 1):
                    combinations += list(itertools.combinations(options, r))
                question['possibleAnswers'] = combinations
        while len(undone_question_ids) > 0:
            p = {'recruitId': recruit_id, 'examId': exam_id, 'stuExamId': student_exam_id,
                 'questionIds': f'[{",".join(undone_question_ids)}]', 'userId': user}
            scores = post('/student/exam/getQuestionDoneState', p)
            undone_question_ids[:] = itertools.filterfalse(
                lambda q: scores[q]['score'] == questions[q]['qscore'], undone_question_ids)
            logger.info(f'{len(undone_question_ids)} questions left.')

            for question_id in undone_question_ids:
                question = questions[question_id]
                c = random.choice(question['possibleAnswers'])
                question['possibleAnswers'].remove(c)
                pa = [{'deviceType': '1', 'examId': str(exam_id), 'userId': str(user),
                       'stuExamId': str(student_exam_id), 'questionId': str(question_id), 'recruitId': str(recruit_id),
                       'answerIds': c, 'dataIds': []}]
                json_str = json.dumps(pa, separators=(',', ':'))
                pb = {'mobileType': 2, 'jsonStr': json_str, 'secretStr': utils.rsa_encrypt(rsa_key, json_str),
                      'versionKey': 1}
                rt = post('/newstudentexam/saveExamAnswer', pb)
                logger.info(rt[0]['messages'])

        if not EXAM_AUTO_SUBMIT:
            continue

        pa = {'deviceType': '1', 'userId': str(user), 'stuExamId': str(student_exam_id), 'recruitId': recruit_id,
              'examId': str(exam_id), 'questionIds': question_ids, 'remainingTime': '0',
              'achieveCount': str(question_ids.__len__())}
        json_str = json.dumps(pa, separators=(',', ':'))
        pb = {'mobileType': 2, 'recruitId': recruit_id, 'examId': str(exam_id), 'userId': user, 'jsonStr': json_str,
              'secretStr': utils.rsa_encrypt(rsa_key, json_str), 'type': exam_type, 'versionKey': 1}
        raw = post('/newstudentexam/submitExamInfo', pb, raw=True)
        rt = json.loads(raw.replace('"{', '{').replace('}"', '}').replace('\\', ''))['rt']
        logger.info(f'{rt["messages"]} Score: {rt["errorInfo"]["score"]}')

    logger.info('Exams done.')
