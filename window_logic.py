# 调用自定义库
# rsa密码加密
import base64
import datetime
import json
# 其他
import os
import re

# 网页
import requests
import rsa
# 界面
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMessageBox, QApplication
from lxml import etree

import verifycodeNet
from window_main import Ui_window_main

# 模式设置
time_restart = 3  # 爬虫重启延迟，!整数!
time_fastReget = 0  # 快速进行重新访问，!整数!
# 网址
urlroot = "https://gmis.buct.edu.cn"
url = urlroot + "/home/stulogin"
# 文件
infoFile = "information.txt"
gifPath = './code.gif'
headers_get = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.26'
}
headers_post = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'Origin': 'https://gmis.buct.edu.cn',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 '
                  'Safari/537.36 Edg/107.0.1418.35',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Microsoft Edge";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


# 处理实际功能类线程
class workThread(QtCore.QThread):
    # 自定义信号—用来和GUI通信
    sinTxt = QtCore.pyqtSignal(str, list)  # 显示输出，str为模式，List为内容，
    sinUnlock = QtCore.pyqtSignal()  # 解锁按钮

    # 初始化
    def __init__(self, parent=None):
        super(workThread, self).__init__(parent)

        # 成员变量
        self.stuID = ""
        self.pwd = ""
        self.method = ""
        self.urlextra = ""
        self.session = requests.session()
        self.runState = False

    # 设置线程成员数值
    def setMethod(self, method):
        # 处理方法 "login"登录网站，"check"查询已报讲座，"enroll"报名讲座
        self.method = method

    def setStuID(self, stuID):
        self.stuID = stuID

    def setPwd(self, pwd):
        self.pwd = pwd

    def setRunState(self, state):
        self.runState = state

    # 重写run方法
    def run(self):
        self.setRunState(True)
        if self.method == "login":
            self.login()
        elif self.method == "check":
            self.check()
        elif self.method == "enroll":
            self.enroll()

    def login(self):
        # 循环直到请求成功
        while 1:
            # 自动重定向
            res = self.session.get(url=url, headers=headers_get)
            self.sinTxt.emit("text", list("正在访问登录网址..."))
            if res.status_code == 200:
                self.sinTxt.emit("text", list("已成功加载登录页面！"))
            else:
                self.sinTxt.emit("text", list("加载登录页面错误，{}s后重新尝试...".format(time_restart)))
                self.sleep(time_restart)
                continue
            # 获取中间额外的url
            self.urlextra = res.url.split("/")[3]
            # 获取验证码url
            tree = etree.HTML(res.text)
            code_img_scr = urlroot + "/" + self.urlextra + "/home/verificationcode?codetype=stucode"
            # 获取验证码图片
            code_img_data = self.session.get(url=code_img_scr, headers=headers_get).content
            self.sinTxt.emit("text", list("正在访问验证码网址..."))
            with open(gifPath, 'wb') as f:
                f.write(code_img_data)
            self.sinTxt.emit("text", list("验证码图片下载成功！"))
            # 识别验证码
            code_string = verifycodeNet.verify(gifPath)

            # 识别失败，退出
            if code_string == "False":
                self.sinTxt.emit("text", list("未能识别出验证码，{}s后刷新界面重试...".format(time_restart)))
                self.sleep(time_restart)
                continue
            self.sinTxt.emit("text", list("识别验证码完毕！"))

            # 密码进行加密
            publicKey = tree.xpath("/html/body/div[2]/input/@value")[0]
            publicKey = changeKey(publicKey)
            pwdEncripted = rsa_encrypt(self.pwd, publicKey)
            self.sinTxt.emit("text", list("密码RSA加密成功！"))

            # 模拟登入
            urllogin = urlroot + "/" + self.urlextra + "/home/stulogin_do"
            # 提交表单
            sheet = {
                "UserId": self.stuID,
                "Password": pwdEncripted,
                "VeriCode": code_string,
                "url": "",
                "city": ""
            }

            # 表单创建json对象
            data = {'json': json.dumps(sheet)}

            res = self.session.post(url=urllogin, headers=headers_post, data=data)
            self.sinTxt.emit("text", list("正在提交登录申请..."))

            # 判断post请求结果
            result = json.loads(res.text)
            if result['jg'] == '1':
                # 登录成功！
                self.sinTxt.emit("text", list("模拟登入成功！"))
                # 解锁讲座信息和自动报名
                self.sinUnlock.emit()
                self.sinTxt.emit("flag", [])
                self.setRunState(False)
                break
            else:
                # 信息错误，登录失败
                msg = result['msg']
                # 判断是验证码错了，还是信息错误
                if msg == "验证码错误":
                    self.sinTxt.emit("text", list("信息出错——{},{}s后刷新界面重试...".format(msg, time_restart)))
                    self.sleep(time_restart)
                    continue
                else:
                    self.sinTxt.emit("text", list("信息出错——{},请重新确认学号密码。".format(msg)))
                    self.setRunState(False)
                    break

    def check(self):
        # 循环直到请求成功
        while 1:
            urlsq = urlroot + "/" + self.urlextra + "/student/yggl/xshdbm_cklist"
            res = self.session.get(url=urlsq, headers=headers_get)
            self.sinTxt.emit("text", list("正在加载已报名讲座..."))
            if res.status_code != 200:
                self.sinTxt.emit("txt", list("未加载到列表，{}s后重新尝试...".format(time_restart)))
                self.sleep(time_restart)
                continue
            self.sinTxt.emit("list", [])
            lists = ["ID号\t报告地点\t\t\t\t\t开始时间\t\t结束时间\t\t审核状态"]
            # 判断是否有接收到数据
            if re.search(r"\[]", res.text):
                self.sinTxt.emit("txt", list("当前未查询到有报名过讲座！"))
            else:
                # 处理列表 最外层：字典'rows':列表   第二层：列表[字典1，字典2...]
                # 取数据转字典
                page_dic = json.loads(res.text)
                # 取所有讲座列表
                lectures = page_dic['rows']
                # 循环输出
                for lecture in lectures:  # lectures为列表，lecture为字典
                    index = lecture['hdid']  # 序列号
                    way = lecture['dd']  # 报名方式
                    time_start = lecture['kssj']  # 报告开始时间
                    time_end = lecture['jzsj']  # 报告结束时间
                    state = lecture['shbj']  # 报告结束时间
                    msg = "{:<6}\t{:<65}\t{}\t{}\t{}".format(index, way, time_start, time_end, state)
                    lists.append(msg)
                self.sinTxt.emit("text", list("查询已报名讲座成功 ！"))
            self.sinTxt.emit("list", lists)
            self.setRunState(False)
            break

    def enroll(self):
        while 1:
            # 加载列表
            urlsq = urlroot + "/" + self.urlextra + "/student/yggl/xshdbm_sqlist"
            # 等待系统响应列表
            res = self.session.get(url=urlsq, headers=headers_get)
            self.sinTxt.emit("text", list("正在访问可报名讲座表单..."))
            if res.status_code != 200:
                self.sinTxt.emit("text", list("未加载到列表，{}s后重新尝试...".format(time_restart)))
                self.sleep(time_restart)
                continue

            self.sinTxt.emit("list", [])
            showLists = ["ID号\t报告地点\t\t\t报名时间\t\t已报/总量\t开始时间\t\t结束时间"]
            idLists = []
            # 判断是否有讲座
            if re.search(r"\[]", res.text):
                pass
            else:
                # 展示所有讲座，选取可以报名的讲座
                # 处理列表 最外层：字典'rows':列表   第二层：列表[字典1，字典2...]
                # 取数据转字典
                page_dic = json.loads(res.text)
                # 取所有讲座列表
                lectures = page_dic['rows']
                # 循环输出
                for lecture in lectures:  # lectures为列表，lecture为字典
                    index = lecture['id']  # 序列号
                    time_enroll = lecture['bmkssj']  # 报名时间
                    way = lecture['dd']  # 报名方式
                    maxNumber = lecture['rs']  # 人数容量
                    number = lecture['bmrs']  # 已报人数
                    time_start = lecture['kssj']  # 报告开始时间
                    time_end = lecture['jzsj']  # 报告结束时间
                    msg = "{:<6}\t{:<25}\t{}\t{}/{}\t{}\t{}".format(index, way, time_enroll, number, maxNumber,
                                                                    time_start, time_end)
                    showLists.append(msg)
                    if int(number) < int(maxNumber):
                        idLists.append(index)
            self.sinTxt.emit("list", showLists)
            # 有可以抢的讲座
            if len(idLists) > 0:
                self.sinTxt.emit("text", list("有{}个讲座可以进行报名！".format(len(idLists))))
                # 依次抢
                for id in idLists:
                    # 循环请求
                    self.sinTxt.emit("text", list("正在抢ID为{}的讲座......".format(id)))
                    while 1:
                        self.sinTxt.emit("text", list("正在访问验证码网址..."))
                        # 获取验证码url
                        code_img_scr = urlroot + "/" + self.urlextra + "/student/yggl/VerificationCode"
                        # 获取验证码图片
                        code_img_data = self.session.get(url=code_img_scr, headers=headers_get).content
                        with open(gifPath, 'wb') as f:
                            f.write(code_img_data)
                        # 识别验证码
                        code_string = verifycodeNet.verify(gifPath)

                        # 识别失败，退出
                        if code_string == "False":
                            self.sinTxt.emit("text", list("验证码识别错误，正在重新尝试..."))
                            self.sleep(time_fastReget)
                            continue

                        data = {
                            "id": id,
                            "VeriCode": code_string
                        }

                        self.sinTxt.emit("text", list("正在提交报名表单..."))
                        ulrEnroll = urlroot + "/" + self.urlextra + "/student/yggl/xshdbm_bm"
                        headers_post['Referer'] = urlroot + "/" + self.urlextra + "/student/yggl/xshdbm"
                        res = self.session.post(url=ulrEnroll, headers=headers_post, data=data)
                        # 判断post请求结果
                        result = json.loads(res.text)

                        if result['zt'] == '1':
                            # 成功拿下！
                            self.sinTxt.emit("text", list("成功抢到ID为{}的讲座！".format(id)))
                            self.setRunState(False)
                            break
                        else:
                            msg = result['msg']
                            if msg == '报名失败':
                                # 依然是成功拿下！不过返回信息有问题
                                self.sinTxt.emit("text", list("成功抢到ID为{}的讲座！".format(id)))
                                self.setRunState(False)
                                break
                            elif msg == "该活动已经满额" or msg == "该活动已经申请！":
                                # 给人抢完了
                                self.sinTxt.emit("text", list("抢取失败——{}".format(msg)))
                                self.setRunState(False)
                                break
                            else:
                                # 预料之外的信息
                                print('----' + res.text + '----')
                                self.sinTxt.emit("text", list("抢取失败——{}，正在重新尝试！".format(msg)))
                                self.sleep(time_fastReget)
                                continue
            else:
                self.sinTxt.emit("text", list("当前没有可进行报名的讲座！"))
                self.setRunState(False)
            break


# 调用功能类线程
class callThread(QtCore.QThread):
    # 自定义信号——用来和GUI通信
    sinCall = QtCore.pyqtSignal()  # 调用线程
    sinLog = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(callThread, self).__init__(parent)
        self.interval = 1  # 发送时间间隔，整数

    def run(self):
        while 1:  # 一直循环
            # 查询当前时间
            time = datetime.datetime.now().time()
            min = time.minute
            sec = time.second

            if (min % 10 == 9 and sec >= 55) or (min % 10 == 0 and sec <= 5):
                # 时间阈值，x9:58->(x+1)0:18
                # 发送信号，让workThread工作
                self.sinCall.emit()
                self.sleep(self.interval)  # 2s发送一次
            elif min % 10 == 9 and sec >= 50:  # 从x9:55开始每1s判断一次
                self.sleep(1)
            else:
                dif = (9 - min % 10) * 60 + (55 - sec)
                self.sinLog.emit("下一个请求时间->{}:{}:55".format(time.hour, min // 10 * 10 + 9))
                self.sleep(dif)


# 逻辑窗口类
class MainWindow(QtWidgets.QMainWindow, Ui_window_main):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        # 控件绑定
        self.checkBox_save.stateChanged.connect(self.saveInfo)
        self.pushButton_getMsg.clicked.connect(self.check)
        self.pushButton_login.clicked.connect(self.login)
        self.pushButton_autoEnroll.clicked.connect(self.judState)

        # 成员属性
        self.session = requests.session()

        # 线程设置
        self.wthread = workThread()
        self.wthread.sinTxt.connect(self.addMsg)  # 检测线程信号的改变，接收并触发函数，附加str变量
        self.wthread.sinUnlock.connect(self.unlock)

        self.cthread = callThread()
        self.cthread.sinCall.connect(self.callThread)
        self.cthread.sinLog.connect(self.addLog)

        #  托盘设置
        self.tray = TrayModel(self)

        # 初始化设置GUI
        self.init()

    # 最小化响应
    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & QtCore.Qt.WindowMinimized:
                event.ignore()
                # 隐藏窗口
                self.hide()
                # 显示托盘图标
                self.tray.show()
                return

    # 初始化
    def init(self):
        # 读取学号和密码
        if os.path.exists(infoFile):
            with open(infoFile, 'r') as f:
                info = f.readlines()
            result = info[0].split('\t')
            stuid = result[0]
            pwd = result[1]
            self.lineEdit_stuid.setText(stuid)
            self.lineEdit_pwd.setText(pwd)
            self.checkBox_save.setChecked(True)
        # 固定窗口大小
        self.setFixedSize(self.width(), self.height())

    # 复选框响应
    def saveInfo(self):  # 保存学号信息
        # 判断是否需要进行保存
        if self.checkBox_save.isChecked():
            stuid = self.lineEdit_stuid.text()
            pwd = self.lineEdit_pwd.text()
            info = stuid + '\t' + pwd
            with open(infoFile, 'w') as f:
                f.write(info)
        else:
            os.remove(infoFile)

    # 线程通信接收函数
    def unlock(self):
        self.pushButton_getMsg.setEnabled(True)
        self.pushButton_autoEnroll.setEnabled(True)

    def addMsg(self, strs, lists):
        if strs == "text":
            msg = "".join(lists)
            self.addLog(msg)
        elif strs == "list":
            if lists == []:
                self.listWidget.clear()
            else:
                self.listWidget.addItems(lists)
            QApplication.processEvents()
        elif strs == "flag":
            self.pushButton_login.setEnabled(False)
            QApplication.processEvents()

    def addLog(self, strs):
        # 判断log文件夹是否存在
        if not os.path.exists('log'):
            os.mkdir('log')
        # 判断log文件是否存在
        logfile = 'log/' + str(datetime.datetime.now().date()) + '.txt'
        # 保存到“日期.log”文件中
        time = datetime.datetime.now().time()
        with open(logfile, 'a+', encoding='utf-8') as f:
            f.write("[{}:{}:{}]\t{}\n".format(time.hour, time.minute, time.second, strs))
        if self.textBrowser_log.toPlainText().count('\n') >= 199:  # 显示信息大于200
            self.textBrowser_log.clear()
        self.textBrowser_log.append(strs)
        self.textBrowser_log.moveCursor(self.textBrowser_log.textCursor().End)
        QApplication.processEvents()

    # 判断是否需要调用workThread
    def callThread(self):
        state = self.wthread.runState
        if state:
            pass
        else:
            self.wthread.setRunState(True)
            self.wthread.start()

    # 按钮响应函数
    def login(self):
        UserID = self.lineEdit_stuid.text()
        password = self.lineEdit_pwd.text()
        if UserID == "" or password == "":
            QMessageBox.information(self, "输入错误！", "请输入学号和密码！", QMessageBox.Ok)
        else:
            # 传递参数
            self.wthread.setMethod("login")
            self.wthread.setStuID(UserID)
            self.wthread.setPwd(password)
            self.wthread.start()

    def check(self):
        self.wthread.setMethod("check")
        self.wthread.start()

    def judState(self):
        state = 0 if self.pushButton_autoEnroll.text() == "自动报名" else 1
        if state:
            # 点击停止
            self.addMsg("text", list("已停止自动抢讲座"))
            self.pushButton_autoEnroll.setText("自动报名")
            self.pushButton_getMsg.setEnabled(True)
            self.wthread.terminate()
            self.cthread.terminate()
            self.wthread.setRunState(False)
        else:
            # 点击自动报名
            self.addMsg("text", list("已启动自动托管抢讲座..."))
            self.addMsg("list", [])
            self.pushButton_autoEnroll.setText("停止")
            self.pushButton_getMsg.setEnabled(False)
            self.wthread.setMethod("enroll")
            self.cthread.start()  # 开始循环检测线程


# 托盘图标类
class TrayModel(QtWidgets.QSystemTrayIcon):
    def __init__(self, MainWindow, parent=None):
        super(TrayModel, self).__init__(parent)
        self.ui = MainWindow
        self.createMenu()

    def createMenu(self):
        # 设置菜单按钮
        self.menu = QtWidgets.QMenu()
        self.actionShow = QtWidgets.QAction("显示", self, triggered=self.showWindow)
        self.actionQuit = QtWidgets.QAction("退出", self, triggered=self.quit)

        self.menu.addAction(self.actionShow)
        self.menu.addAction(self.actionQuit)
        self.setContextMenu(self.menu)

        # 设置图标
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/ico/icon.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setIcon(icon)
        self.icon = self.MessageIcon()

        # 把鼠标点击图标的信号和槽连接
        self.activated.connect(self.onIconClicked)

    def showWindow(self):
        # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
        self.ui.showNormal()
        self.ui.activateWindow()
        self.hide()

    def quit(self):
        QtWidgets.qApp.quit()

    # 鼠标点击icon传递的信号会带有一个整形的值，1是表示单击右键，2是双击，3是单击左键，4是用鼠标中键点击
    def onIconClicked(self, reason):
        if reason == 2 or reason == 3:
            if self.ui.isMinimized() or not self.ui.isVisible():
                # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
                self.ui.showNormal()
                self.ui.activateWindow()
                self.ui.setWindowFlags(QtCore.Qt.Window)
                self.ui.show()
                self.hide()


# RAS加密
def changeKey(string):
    first = string.find("\n")
    last = string.rfind("\n", 0, -2)
    string = string[first + 1:last - 1]
    string = string.replace('\n', '')
    return string


def _str2key(s):
    # 对字符串解码
    b_str = base64.b64decode(s)

    if len(b_str) < 162:
        return False

    hex_str = ''

    # 按位转换成16进制
    for x in b_str:
        h = hex(x)[2:]
        h = h.rjust(2, '0')
        hex_str += h

    # 找到模数和指数的开头结束位置
    m_start = 29 * 2
    e_start = 159 * 2
    m_len = 128 * 2
    e_len = 3 * 2

    modulus = hex_str[m_start:m_start + m_len]
    exponent = hex_str[e_start:e_start + e_len]

    return modulus, exponent


def rsa_encrypt(s, pubkey_str):
    """
    rsa加密
    :param s:
    :param pubkey_str:公钥
    :return:
    """
    key = _str2key(pubkey_str)
    modulus = int(key[0], 16)
    exponent = int(key[1], 16)
    pubkey = rsa.PublicKey(modulus, exponent)
    return base64.b64encode(rsa.encrypt(s.encode(), pubkey)).decode()


# 保存网页
def saveHtml(res, fileName):
    res.encoding = 'utf-8'
    with open(fileName + '.html', 'w', encoding='utf-8') as f:
        f.write(res.text)
