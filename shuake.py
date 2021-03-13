import urllib.request, urllib.parse
import http.cookiejar
import requests
import json
import os
import re
from moviepy.editor import VideoFileClip
import time
import random


def login():
    global Token
    global headers
    Token = {}
    username = input("请输入用户名：")
    password = input("请输入密码：")
    cookie = http.cookiejar.CookieJar()
    handler = urllib.request.HTTPCookieProcessor(cookie)
    opener = urllib.request.build_opener(handler)
    login_url = "https://www.ulearning.cn/umooc/user/login.do"
    values = {
        "name": username,
        "passwd": password,
        "yancode": "",
        "redirectURL": "",
        "isFrom": "",
        "newLocale": ""
    }
    postdata = urllib.parse.urlencode(values).encode("UTF-8")
    response = opener.open(login_url, data=postdata)
    for item in cookie:
        Token[item.name] = urllib.parse.unquote(item.value)
    if 'AUTHORIZATION' in Token and 'token' in Token and 'UMOOC_SESSION' in Token:
        with open('./cookies.txt', 'wb', True) as f:
            f.write(json.dumps(Token).encode('UTF-8'))
        headers = {
            'UA-AUTHORIZATION': Token['token'],
            'AUTHORIZATION': Token['AUTHORIZATION'],
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'
        }
        return ("登陆成功...")
    else:
        print("用户名或密码错误，登陆失败")
        login()


def get_courses_list():
    global headers
    get_courses_list_api = "https://courseapi.ulearning.cn/courses/students?keyword=&publishStatus=1&type=1&pn=1&ps=15"
    response = requests.request(method='GET', url=get_courses_list_api, headers=headers)
    if 'code' in response.json() and response.json()['code'] == 2101:
        with open('./cookies.txt', 'wb', True) as f:
            f.truncate()
        print("身份已过期请重新登陆")
        login()
        return get_courses_list()
    else:
        return response.json()['courseList']


def get_course_chapters_list(coursesId):
    global headers
    get_textbookId_api = "https://courseapi.ulearning.cn/textbook/student/%d/list" % coursesId
    # 获取该课程的子课程
    response = requests.request(method='GET', url=get_textbookId_api, headers=headers)
    listJson = response.json()
    # 获取班级ID
    get_course_classId_api = "https://courseapi.ulearning.cn/classes/information/student/%d" % coursesId
    response2 = requests.request(method='GET', url=get_course_classId_api, headers=headers)
    classData = response2.json()
    i = 0
    data = {
        'textbook': [],
        'classInfo': ''
    }
    while i < len(listJson):
        textbookId = listJson[i]['courseId']
        get_course_chapters_list_api = "https://courseapi.ulearning.cn/textbook/student/information?ocId=%d&textbookId=%d" % (
        coursesId, textbookId)
        response3 = requests.request(method='GET', url=get_course_chapters_list_api, headers=headers)
        data['textbook'].append(response3.json()['textbook'])
        i += 1
    data['classInfo'] = classData
    return data


def get_chapters_item(textbookId, classId):
    global headers
    get_directory_info_api = "https://api.ulearning.cn/course/stu/%d/directory?classId=%d" % (textbookId, classId)
    response = requests.request(method='GET', url=get_directory_info_api, headers=headers)
    return response.json()


def get_every_section(nodeid, itemsInfo):
    global headers
    get_every_section_api = "https://api.ulearning.cn/wholepage/chapter/stu/%d" % nodeid
    response = requests.request(method='GET', url=get_every_section_api, headers=headers)
    sectionDict = response.json()
    get_user_info_api = "https://api.ulearning.cn/user"
    response2 = requests.request(method='GET', url=get_user_info_api, headers=headers)
    userInfoDict = response2.json()
    k = 0
    while k < len(sectionDict['wholepageItemDTOList']):
        check_section(sectionDict['wholepageItemDTOList'][k], userInfoDict, itemsInfo[k])
        k += 1


def check_answer(coursepageDTOList):
    global headers
    print("检测到题目，开始自动答题.....")
    questions = {}
    questionsIds = []
    parentIds = []
    questionsData = []
    i = 0
    while i < len(coursepageDTOList):
        if coursepageDTOList[i]['questionDTOList']:
            parentIds.append(coursepageDTOList[i]['parentid'])
            j = 0
            while j < len(coursepageDTOList[i]['questionDTOList']):
                if coursepageDTOList[i]:
                    questionsIds.append(coursepageDTOList[i]['questionDTOList'][j]['questionid'])
                j += 1
        i += 1
    questionsIdList = list(set(questionsIds))
    for parentId in parentIds:
        l = 0
        while l < len(questionsIdList):
            get_answer_api = "https://api.ulearning.cn/questionAnswer/%d?parentId=%d" % (questionsIdList[l], parentId)
            response = requests.request(method='GET', url=get_answer_api, headers=headers)
            answerJson = response.json()
            if answerJson['subQuestionAnswerDTOList']:
                n = 0
                while n < len(answerJson['subQuestionAnswerDTOList']):
                    questions['questionid'] = answerJson['subQuestionAnswerDTOList'][n]['questionid']
                    questions['answerList'] = answerJson['subQuestionAnswerDTOList'][n]['correctAnswerList']
                    questions['score'] = 100
                    print("第%d道大题的第%d小题答案获取完毕，准备提交..." % (l + 1, n + 1))
                    questionsData.append(questions.copy())
                    n += 1
            else:
                questions['questionid'] = answerJson['questionid']
                questions['answerList'] = answerJson['correctAnswerList']
                questions['score'] = 100
                questionsData.append(questions.copy())
            print("第%d道大题的答案获取完毕，准备提交..." % (l + 1))
            l += 1
    return questionsData


def speakingEnglish(coursepageDTOList, itemid, relationid):
    global headers
    print("检测到英语读单词")
    status = int(input("0代表自动(会选择示范音，易封号)，1代表刷分(需要提前读一遍单词)，请选择模式："))
    speak = []
    speaks = {}
    if status == 0:
        i = 0
        while i < len(coursepageDTOList):
            if coursepageDTOList[i]['speak']:
                j = 0
                while j < len(coursepageDTOList[i]['speak']['audresp']):
                    speaks['speakingid'] = coursepageDTOList[i]['speak']['audresp'][j]['audioid']
                    speaks['score'] = 100
                    speaks['time'] = random.randint(1, 4)
                    speaks['url'] = coursepageDTOList[i]['speak']['audresp'][j]['audiofileFullurl']
                    direction = coursepageDTOList[i]['speak']['audresp'][j]['direction'].split()
                    num = len(direction)
                    if num > 1:
                        k = 0
                        str = "["
                        while k < num:
                            str += '{\\"%s\\":100}' % direction[k] + ","
                            k += 1
                        str = str.rstrip(",")
                        str += "]"
                        speaks['answer'] = str
                    else:
                        speaks['answer'] = "[{\"%s\":100}]" % direction[0]
                    speak.append(speaks.copy())
                    j += 1
            i += 1

    if status == 1:
        api = "https://api.ulearning.cn/studyrecord/item/%s?courseType=4" % itemid
        response = requests.request(method='GET', url=api, headers=headers)
        res = response.json()
        i = 0
        while i < len(res['pageStudyRecordDTOList']):
            if res['pageStudyRecordDTOList'][i]['pageid'] == relationid and res['pageStudyRecordDTOList'][i][
                'speaks'] and res['pageStudyRecordDTOList'][i]['studyTime'] != 0:
                j = 0
                while j < len(res['pageStudyRecordDTOList'][i]['speaks']):
                    if res['pageStudyRecordDTOList'][i]['speaks'][j]['url']:
                        speaks['speakingid'] = res['pageStudyRecordDTOList'][i]['speaks'][j]['speakingid']
                        speaks['score'] = 100
                        speaks['time'] = res['pageStudyRecordDTOList'][i]['speaks'][j]['time']
                        speaks['url'] = res['pageStudyRecordDTOList'][i]['speaks'][j]['url']
                        speaks['answer'] = re.sub(r'\d+', "100",
                                                  res['pageStudyRecordDTOList'][i]['speaks'][j]['answer'])
                        speak.append(speaks.copy())
                    else:
                        print("检测到该题未找到音频，将不会上传")
                    j += 1
            i += 1
        response.close()
    if speak:
        return speak
    else:
        print("程序故障")
        return False


def check_section(wholepageItemDTOList, userInfo, itemsInfo):
    global headers
    now_time = int(time.time())
    cryptoJsonData = {
        'itemid': wholepageItemDTOList['itemid'],
        'autoSave': 1,
        'version': 'null',
        'withoutOld': 'null',
        'complete': 1,
        'studyStartTime': now_time,
        'score': 100,
        'userName': userInfo['name'],
        'pageStudyRecordDTOList': []
    }
    if itemsInfo:
        title = itemsInfo['title']
    else:
        try:
            get_item_title_api = "https://api.ulearning.cn/studyrecord/item/%s?courseType=4" % wholepageItemDTOList[
                'itemid']
            response = requests.request(method='GET', url=get_item_title_api, headers=headers)
            title = response.json()['activity_title']
            response.close()
        except:
            title = "未获取到标题"

    studyTime = int(input("请输入本章的%s小节需要的时间(以秒为单位，建议在400-1000，数据过大易封号，时间是叠加的，为0则时间保持不变，负数则时间回退)：" % title))
    temple = {
        'pageid': 0,
        'complete': 1,
        'studyTime': studyTime,
        'score': 100,
        'answerTime': 1,
        'submitTimes': 0,
        'questions': [],
        'videos': [],
        'speaks': [],
    }
    i = 0
    while i < len(wholepageItemDTOList['wholepageDTOList']):
        k = 0
        while k < len(wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList']):
            if 'resourceFullurl' in wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList'][k]:
                resourceFullurl = wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList'][k]['resourceFullurl']
                if resourceFullurl == None:
                    pass
                elif resourceFullurl.find('mp4') > 0:
                    # 防止测验题里面有视频
                    videoId = wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList'][k]['resourceid']
                    print("为了数据真实性，正在获取视频时长，过程缓慢，请耐心等待...")
                    clip = VideoFileClip(resourceFullurl)
                    print("此视频数据获取完毕...")
                    if videoId:
                        videos = {
                            'videoid': videoId,
                            'current': 100 + clip.duration,
                            'status': 1,
                            'recordTime': clip.duration,
                            'time': clip.duration,
                            'startEndTimeList': [{
                                'startTime': now_time,
                                'endTime': now_time + studyTime,
                            }]
                        }
                    temple['videos'].append(videos)
                    clip.close()
                    time.sleep(2)
                    print("开启下一项任务...")
            k += 1
        # 图文型
        if wholepageItemDTOList['wholepageDTOList'][i]['contentType'] == 5:
            pass

        # 英语读单词
        if wholepageItemDTOList['wholepageDTOList'][i]['content'] == 'Speaking':
            speaks = speakingEnglish(wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList'],
                                     wholepageItemDTOList['itemid'],
                                     wholepageItemDTOList['wholepageDTOList'][i]['relationid'])
            temple['speaks'] = speaks

        # 测验型
        if wholepageItemDTOList['wholepageDTOList'][i]['contentType'] == 7:
            questions = check_answer(wholepageItemDTOList['wholepageDTOList'][i]['coursepageDTOList'])
            temple['questions'] = questions

        temple['pageid'] = wholepageItemDTOList['wholepageDTOList'][i]['relationid']
        cryptoJsonData['pageStudyRecordDTOList'].append(temple)
        i += 1
        print(cryptoJsonData)
        postJsonStr = json.dumps(cryptoJsonData)
        headers['Content-Type'] = 'text/plain'
        response = requests.request(method='POST', url="https://pay.ufec.cn/getSign.php", headers=headers,
                                    data=postJsonStr)

        payload = response.text
        response2 = requests.request(method='POST',
                                     url="https://api.ulearning.cn/yws/api/personal/sync?courseType=4&platform=PC",
                                     headers=headers, data=payload)
        response2.close()
        print("%s小节已刷完，等待下一节命令执行中......" % title)


if __name__ == "__main__":
    global Token
    global headers
    print("欢迎使用优学院刷课脚本， 工具只是辅助作用切勿用来盈利，一切后果与作者无关")
    try:
        f = open('./cookies.txt')
        f.close()
    except FileNotFoundError:
        # 创建空白文件
        open('./cookies.txt', 'w')
    except PermissionError:
        exit("You don't have permission to access this file")
    size = os.path.getsize('./cookies.txt')
    if size == 0:
        print("开始登陆....")
        login()
    else:
        with open('./cookies.txt', 'r') as f:
            s = f.read()
        Token = dict(json.loads(s))

    headers = {
        'UA-AUTHORIZATION': Token['token'],
        'AUTHORIZATION': Token['AUTHORIZATION'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'
    }
    resJson = get_courses_list()
    total = len(resJson)
    print("一共获取到%d门课程" % total)
    i = 0
    while i < total:
        print("课程编号：%d 课程名称：%s" % (i, resJson[i]['name']))
        i += 1
    coursesId = int(input("请选择课程编号："))
    if coursesId > total - 1:
        exit("你哪只眼睛看到了有这个编号？？？")
    print("当前课程编号为：%d; 课程名称：%s" % (coursesId, resJson[coursesId]['name']))
    print("开始获取课程章节....")
    course_chapters_list_data = get_course_chapters_list(resJson[coursesId]['id'])
    textbookNum = len(course_chapters_list_data['textbook'])
    print("该课程下有%d门小课程" % textbookNum)
    j = 0
    while j < textbookNum:
        print("第%d门小课程，课程编号为：%d，课程名为：%s" % (j + 1, j, course_chapters_list_data['textbook'][j]['courseName']))
        j += 1
    if textbookNum == 1:
        chooseTextbookId = 0
    else:
        chooseTextbookId = int(input("请输入小课程编号:"))

    if chooseTextbookId > textbookNum - 1:
        exit("你哪只眼睛看到了有这个编号？？？")

    courseName = course_chapters_list_data['textbook'][chooseTextbookId]['courseName']
    print("当前所选课程编号为：%d，课程名为%s" % (chooseTextbookId, courseName))
    textbookId = course_chapters_list_data['textbook'][chooseTextbookId]['courseId']
    classId = course_chapters_list_data['classInfo']['classId']
    print("正在获取%s课程下的章节内容" % courseName)
    chapters_item_dict = get_chapters_item(textbookId, classId)
    chaptersNum = len(chapters_item_dict['chapters'])
    coursename = chapters_item_dict['coursename']
    print("%s下共有%d章节" % (coursename, chaptersNum))
    print("是否开启刷全章，开启输入1，不开启输入0(为了安全起见建议不要全章节刷)")
    status = int(input("请选择："))
    if status == 1:
        k = 0
        while k < chaptersNum:
            print("当前选章节编号为%d，章节名称为：%s" % (k, chapters_item_dict['chapters'][k]['nodetitle']))
            print("正在获取%s章节下所有小节内容" % chapters_item_dict['chapters'][k]['nodetitle'])
            get_every_section(chapters_item_dict['chapters'][k]['nodeid'], chapters_item_dict['chapters'][k]['items'])
            k += 1
    elif status == 0:
        k = 0
        while k < chaptersNum:
            print("章节编号%d，章节名称：%s" % (k, chapters_item_dict['chapters'][k]['nodetitle']))
            k += 1
        str = input("请选择章节编号，多个章节请用英文逗号,隔开：")
        strList = list(str.split(','))
        i = 0
        chapterList = []
        while i < len(strList):
            if strList[i] and strList[i].isdigit():
                chapterList.append(strList[i])
            else:
                print("该项没有合法章节编号或分隔符使用错误。已被过滤")
            i += 1
        j = 0
        while j < len(chapterList):
            if int(chapterList[j]) <= chaptersNum:
                chapterList[j] = int(chapterList[j])
                print("当前选章节编号为%d，章节名称为：%s" % (
                chapterList[j], chapters_item_dict['chapters'][chapterList[j]]['nodetitle']))
                print("正在获取%s章节下所有小节内容" % chapters_item_dict['chapters'][chapterList[j]]['nodetitle'])
                get_every_section(chapters_item_dict['chapters'][chapterList[j]]['nodeid'],
                                  chapters_item_dict['chapters'][chapterList[j]]['items'])
            j += 1
        end = 0
        while end != 1:
            end = int(input("本次任务执行完毕，输入1退出："))
    else:
        exit("输入有误，程序结束")
