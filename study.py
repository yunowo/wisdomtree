import logging
import json
import datetime
from getpass import getpass
import requests
from Cryptodome.PublicKey import RSA

import utils

SERVER = 'https://appserver.zhihuishu.com/app-web-service'
SSL_VERIFY = True
TAKE_EXAMS = True
EXAM_AUTO_SUBMIT = True

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG)
    logger = logging.getLogger()

    key = RSA.importKey(open('key.pem', 'r').read())

    s = requests.Session()
    s.headers.update(
        {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.0; Nexus 5X Build/NRD90S', 'Accept-Encoding': 'gzip'})
    s.cookies.update({'Z_LOCALE': '2', 'SERVERID': '452f6013e2e3da3c556933e21006fcf4|1473776004|1473775975'})

    logger.info('I love studying! Study makes me happy!')


    def login():
        account = input('Account(Phone):')
        password = getpass(prompt='Password:')
        assert account or password

        p = {'mobileVersion': '2.7.0', 'mobileType': 1, 'account': account, 'password': password, 'appType': 1}
        r = s.post(SERVER + '/appserver/base/loginApp', data=p, verify=SSL_VERIFY)
        d = r.json()['rt']
        u = d['id']
        n = d['realName']
        logger.info(n + ' ' + str(u))
        with open('userinfo.py', 'w+', encoding='utf-8') as f:
            f.writelines('USER = ' + str(u) + '\n')
            f.writelines('NAME = "' + n + '"')
        logger.info('Login OK.')
        return u, n


    try:
        import userinfo

        user = userinfo.USER
        name = userinfo.NAME
        if input('Current user:' + name + ' ' + str(user) + ':[y/n]') != 'y':
            user, name = login()
    except:
        user, name = login()

    p = {'userId': user}
    r = s.post(SERVER + '/appserver/online/findAllCourseList', data=p, verify=SSL_VERIFY)
    course_id, recruit_id, link_course_id = 0, 0, 0
    for course in r.json()['rt']['studyList']:
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
        video_time = dic['videoSec']
        chapter_id = chapter_id or dic['chapterId']
        j = {'lessonId': lesson_id, 'learnTime': str(datetime.timedelta(seconds=video_time)), 'userId': user,
             'personalCourseId': link_course_id, 'recruitId': recruit_id, 'chapterId': chapter_id, 'sourseType': 3,
             'playTimes': video_time, 'videoId': dic['videoId']}
        if lesson_id is None:
            j['lessonId'] = dic['id']
        else:
            j['lessonVideoId'] = dic['id']
        jsonstr = json.dumps(j, sort_keys=True, separators=(',', ':'))
        secret = utils.rsa_encrypt(key, bytes(jsonstr, encoding="utf-8"))
        p = {'jsonStr': jsonstr, 'secretStr': secret, 'versionKey': 1}
        r = s.post(SERVER + '/student/tutorial/saveLearningRecord', data=p, verify=SSL_VERIFY)
        logger.info(dic['name'] + r.json()['studyPercenter'])


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

    p = {'mobileType': 1, 'recruitId': recruit_id, 'courseId': course_id, 'page': 1, 'userId': user, 'examType': 1,
         'pageSize': 20}  # examType=2 is finished exams
    r = s.post(SERVER + '/appserver/exam/findAllExamInfo', data=p, verify=SSL_VERIFY)
    for exam in r.json()['rt']['stuExamDtoList']:
        logger.info(exam['examInfoDto']['name'])
        if exam['examInfoDto']['type'] == 2:  # Final exams
            logger.info('Skipped final exam.')
            continue
        exam_id = exam['examInfoDto']['examId']
        student_exam_id = exam['studentExamInfoDto']['id']
        question_ids = []

        p = {'appType': 1, 'userId': user, 'studentExamId': student_exam_id}
        r = s.post(SERVER + '/student/exam/examQuestionIdList', data=p, verify=SSL_VERIFY)
        for question in r.json()['rt']['examList']:
            question_id = question['questionId']
            p['questionId'] = question_id
            question_ids.append(str(question_id))

            r = s.post(SERVER + '/student/exam/questionInfo', data=p, verify=SSL_VERIFY)
            d = r.json()['rt']
            logger.info(d['firstname'])
            if d['questionTypeName'] == '多选题' or '单选题':
                answer = d['realAnswer'].split(',')
            else:
                EXAM_AUTO_SUBMIT = False
                continue

            pa = [{'deviceType': '1', 'examId': str(exam_id), 'userId': str(user), 'stuExamId': str(student_exam_id),
                   'questionId': str(question_id), 'recruitId': str(recruit_id), 'answerIds': answer, 'dataIds': []}]
            pb = {'json': json.dumps(pa, separators=(',', ':'))}
            r = s.post(SERVER + '/appserver/exam/saveExamAnswer', data=pb, verify=SSL_VERIFY)
            logger.info(r.json()['rt'][0]['messages'])
        if not EXAM_AUTO_SUBMIT:
            continue

        pa = {'deviceType': '1', 'userId': str(user), 'stuExamId': str(student_exam_id),
              'questionIds': question_ids, 'remainingTime': '0', 'achieveCount': str(question_ids.__len__())}
        pb = {'mobileType': 2, 'userId': user, 'json': json.dumps(pa, separators=(',', ':'))}
        r = s.post(SERVER + '/appserver/exam/submitExamInfo', data=pb, verify=SSL_VERIFY)
        d = json.loads(r.text.replace('"{', '{').replace('}"', '}').replace('\\', ''))['rt']
        logger.info(d['messages'] + ' Score: ' + d['errorInfo']['score'])

    logger.info('Exams done.')
