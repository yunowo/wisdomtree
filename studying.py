import logging
import json
import datetime
import requests
from Cryptodome.PublicKey import RSA

import utils
import userinfo

SSL_VERIFY = False
SERVER = 'https://appserver.zhihuishu.com/app-web-service'

if __name__ == '__main__':
    user = userinfo.USER

    logging.basicConfig(format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s', level=logging.DEBUG)
    logger = logging.getLogger()

    key = RSA.importKey(open('key.pem', 'r').read())

    s = requests.Session()
    s.headers.update(
        {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.0; Nexus 5X Build/NRD90S', 'Accept-Encoding': 'gzip'})
    s.cookies.update({'Z_LOCALE': '2'})

    logger.info('I love studying! Study makes me happy!')
    p = {'userId': user}
    r = s.post(SERVER + '/appserver/online/findAllCourseList', data=p, verify=SSL_VERIFY)
    course_id, recruit_id, link_course_id = 0, 0, 0
    for course in r.json()['rt']['studyList']:
        if input(course['courseName'] + ':[y/n]') == 'y':
            course_id = course['courseId']
            recruit_id = course['recruitId']
            link_course_id = course['linkCourseId']
            continue
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

    logger.info('Done.')
