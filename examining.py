import json
import logging
import requests

import userinfo

SSL_VERIFY = True
SERVER = 'https://appserver.zhihuishu.com/app-web-service'
AUTO_SUBMIT = True

if __name__ == '__main__':
    user = userinfo.USER

    logging.basicConfig(format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s', level=logging.DEBUG)
    logger = logging.getLogger()

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

    p = {'mobileType': 1, 'recruitId': recruit_id, 'courseId': course_id, 'page': 1, 'userId': user, 'examType': 1,
         'pageSize': 20}  # examType=2 is finished exams
    r = s.post(SERVER + '/appserver/exam/findAllExamInfo', data=p, verify=SSL_VERIFY)
    for exam in r.json()['rt']['stuExamDtoList']:
        if exam['examInfoDto']['type'] == 2:  # Final exams
            continue
        logger.info(exam['examInfoDto']['name'])
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
                AUTO_SUBMIT = False
                continue

            pa = [{'deviceType': '1', 'examId': str(exam_id), 'userId': str(user), 'stuExamId': str(student_exam_id),
                   'questionId': str(question_id), 'recruitId': str(recruit_id), 'answerIds': answer, 'dataIds': []}]
            pb = {'json': json.dumps(pa, separators=(',', ':'))}
            r = s.post(SERVER + '/appserver/exam/saveExamAnswer', data=pb, verify=SSL_VERIFY)
            logger.info(r.json()['rt'][0]['messages'])
        if not AUTO_SUBMIT:
            continue
        pa = {'deviceType': '1', 'userId': str(user), 'stuExamId': str(student_exam_id),
              'questionIds': question_ids, 'remainingTime': '0', 'achieveCount': str(question_ids.__len__())}
        p = {'mobileType': 2, 'userId': user, 'json': json.dumps(pa, separators=(',', ':'))}
        r = s.post(SERVER + '/appserver/exam/submitExamInfo', data=p, verify=SSL_VERIFY)
        d = r.json()['rt']
        logger.info(d['messages'] + ' Score: ' + d['errorInfo']['score'])
    logger.info('Done.')
