from datetime import datetime
from ftplib import FTP
from dateutil import parser
import os
import time
import tkinter as tk
import ctypes
import send2trash
from PIL import Image, ImageTk

update = [] # 记录更新的文件
error = [] # 记录复制失败的文件
redundant = [] # 记录本机比服务器多的文件

# 从ftp服务器段下载文件
def getFile(ftp, rootFolder, filename, savedir):
    try:
        ftp.retrbinary("RETR " + rootFolder + filename ,open(savedir+filename, 'wb').write)
    except:
        print("Error! " + savedir+filename)
        error.append(savedir+filename)

# 简单判断是文件夹还是文件名
def isdir(filaname):
    content = filaname.split('.')
    if len(content) == 1:
        return True
    return False

# 同步文件夹，以及子文件夹（服务器有，但本地没有的文件会被复制；服务器有，且本地也有的文件，根据时间戳判断是否需要更新；但是本地有，而服务器没有的文件，此函数不会删除本地的这种文件）
def SyncFolder(ftp, rootFolder, savedir):
    lines = []
    ftp.dir(rootFolder, lines.append) # 获取文件名以及时间戳
    for line in lines:
        tokens = line.split(maxsplit = 9)
        filename = tokens[8] # 服务器里的文件名
        if not isdir(filename): 
        # 是文件才传输 
            source_time_str = tokens[5] + " " + tokens[6] + " " + tokens[7] # 时间戳
            source_time = parser.parse(source_time_str) # 根据时间戳得到服务器文件的上次修改时间
            if os.path.isfile(savedir+filename):
                save_timestamp = os.path.getmtime(savedir + filename)
                save_time = datetime.fromtimestamp(time.mktime(time.localtime(save_timestamp))) # 根据时间戳得到本地文件的修改时间
            else:
                save_time = datetime(1970,1,1) # 目标文件夹没有该文件，设置默认时间为很早以前

            if source_time > save_time:
                update.append({savedir+filename,source_time})
                getFile(ftp, rootFolder, filename, savedir) # 服务器文件修改过才更新
        else:
        # 是文件夹，进入该文件夹，然后递归调用
            if not os.path.isdir(savedir+filename):
                os.mkdir(savedir+filename+'/') # 在本机创建不存在的文件夹
            SyncFolder(ftp, rootFolder=rootFolder + filename + '/', savedir=savedir+filename+'/')
        
# 本地有，而服务器没有的文件，此函数将记录这种文件及其路径，方便后面决定是否删除
def FindRedundantFiles(ftp, LocalFolder, ftpFloder):
    filenames = os.listdir(LocalFolder) # 列出所有文件
    for filename in filenames:
        if filename not in ftp.nlst(ftpFloder):
            # print('file redundant: ', LocalFolder+filename) 
            redundant.append(LocalFolder+filename)# 不在ftp服务器的就是多余的
        else:
            if os.path.isdir(LocalFolder+filename): # 在服务器中，但是是文件夹的，递归进入文件夹寻找
                FindRedundantFiles(ftp, LocalFolder=LocalFolder+filename+'/', ftpFloder=ftpFloder+filename+'/')

def DeleteFileList(FileList):
    length = len(FileList)
    # for file in FileList:
    while FileList != []:
        file = FileList.pop()
        if os.path.isfile(file):
            # os.remove(file) # 风险太大
            send2trash.send2trash(file)# 回收站比较保险
        else:
            if not len(os.listdir(file)):
                # os.removedirs(file) # 空文件夹就删除, 风险太大
                send2trash.send2trash(file)# 空文件夹放入回收站，回收站比较保险
            else: # 非空文件夹，列举出其中的文件递归
                newlist = [file + '/' + x for x in os.listdir(file)]
                DeleteFileList(newlist)
    if length >= 1:
        print('All redundant files deleted')
    

def readconfig():
    with open('ftpSync.config', 'r', encoding='utf-8') as reader:
        content = reader.read()
    return (content.split('\n'))
    
def writeconfig(
    host,
    port,
    user,
    password,
    ftpFolder,
    saveFolder,):
    with open('ftpSync.config', 'w', encoding='utf-8') as writer:
        writer.write(host+'\n')
        writer.write(str(port)+'\n')
        writer.write(user+'\n')
        writer.write(password+'\n')
        writer.write(ftpFolder+'\n')
        writer.write(saveFolder)

# 可视化界面
def main_window():
    host = '192.168.137.177'
    port = 3721
    user = 'BravoDesmond'
    password = '57474741hjb,'
    ftpFolder = '我的文件/' # ftp服务器端的读取的路径
    saveFolder = 'save/' # 保存到本机的路径

    contents =readconfig()
    if len(contents) == 6:
        host = contents[0]
        port = int(contents[1])
        user = contents[2]
        password = contents[3]
        ftpFolder = contents[4]
        saveFolder = contents[5]
    
    if not os.path.isdir(saveFolder[:-1]):
        os.mkdir(saveFolder)
    # 声名全局变量
    window = tk.Tk()
    window.title("Desmond's Drive") # window title
    window.geometry("400x400") # window size
    window.config(bg='white')
    # 获取窗口的宽高
    window.update() # 不更新的话得到的宽高是1
    win_hei = window.winfo_height()
    win_wid = window.winfo_width()

    ################################# 显示一个图片作为logo ###############################
    logo_img = ImageTk.PhotoImage(Image.open('logo.png').resize((90, 90)))
    # logo_img = ImageTk.PhotoImage(Image.open(r'logo.png'))
    logo = tk.Label(window, image=logo_img, bg='white')
    logo.pack(side='top')

    ################################# Host输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    length1 = 84
    input_hint = tk.Label(window, text='Host:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1-14, y=-40+win_hei / 2 - 40) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_host = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_host.place(x=length1 - 8 + input_hint.winfo_width(), y=-40+win_hei / 2-39) # 选择放置的位置
    input_entry_host.insert(0, host)
    # 操作提示框
    hint00 = tk.Label(window, text='', bg='white', font=('微软雅黑', 12))
    hint00.pack(side='bottom')

    ################################# Port输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='Port:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1-12, y=-40+win_hei / 2 - 15) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_port = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_port.place(x=length1 - 5 + input_hint.winfo_width(), y=-40+win_hei / 2 - 15) # 选择放置的位置
    input_entry_port.insert(0, port)

    ################################# UserName输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='User:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 12, y=-40+win_hei / 2+10) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_user = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_user.place(x=length1 - 7 + input_hint.winfo_width(), y=-40+win_hei / 2 +10) # 选择放置的位置
    input_entry_user.insert(0, user)
    ################################# Password输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='Password:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1-50, y=-40+win_hei / 2 + 35) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_password = tk.Entry(window, font=('微软雅黑', 12), width=18, show='*') # show='*'使得输入的字符全部显示为'*'
    input_entry_password.place(x=length1 - 45 + input_hint.winfo_width(), y=-40+win_hei / 2 + 35) # 选择放置的位置
    input_entry_password.insert(0, password)
    ################################# ftpFolder输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='ftpFloder:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 48, y=-40+win_hei / 2+60) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_ftpFolder = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_ftpFolder.place(x=length1 - 43 + input_hint.winfo_width(), y=-40+win_hei / 2 +60) # 选择放置的位置
    input_entry_ftpFolder.insert(0,ftpFolder)
    ################################# UserName输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='SaveFloder:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 61, y=-40+win_hei / 2+85) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_saveFolder = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_saveFolder.place(x=length1 - 56 + input_hint.winfo_width(), y=-40+win_hei / 2 +85) # 选择放置的位置
    input_entry_saveFolder.insert(0, saveFolder)

    def apply():
        host = input_entry_host.get()
        port = int(input_entry_port.get())
        user = input_entry_user.get()
        password = input_entry_password.get()
        ftpFolder = input_entry_ftpFolder.get()
        saveFolder = input_entry_saveFolder.get()
        writeconfig(port=port, host=host,user=user,password=password,saveFolder=saveFolder,ftpFolder=ftpFolder)
        try:
            # 连接ftp
            ftp = FTP()
            ftp.encoding = 'utf-8'
            ftp.connect(host=host, port=port)
            ftp.login(user, password)
            hint00.config(text='登录成功，正在同步')
            
            SyncFolder(ftp=ftp, rootFolder=ftpFolder, savedir=saveFolder) # 同步文件夹
            FindRedundantFiles(ftp=ftp, LocalFolder=saveFolder, ftpFloder=ftpFolder) # 找出本地端多余的文件

            print(str(len(update)) + ' following files were updated:\n', update)
            print(str(len(error)) + ' following files failed to fetch:\n', error)
            print(str(len(redundant)) + ' following files are redundant:\n', redundant)
            # 延迟，让提示显示一会儿
            window.update()
            window.after(600)
            hint00.config(text='')

            ftp.quit()
        except:
            print('操作失败或登录不成功，请核对端口、主机名、用户名以及密码')
            hint00.config(text='操作失败或登录不成功，请核对端口、主机名、用户名以及密码')
            # 延迟，让提示显示一会儿
            window.update()
            window.after(600)
            hint00.config(text='')
    
    def apply2():
        global redundant
        host = input_entry_host.get()
        port = int(input_entry_port.get())
        user = input_entry_user.get()
        password = input_entry_password.get()
        ftpFolder = input_entry_ftpFolder.get()
        saveFolder = input_entry_saveFolder.get()
        writeconfig(port=port, host=host,user=user,password=password,saveFolder=saveFolder,ftpFolder=ftpFolder)

        try:
            # 连接ftp
            ftp = FTP()
            ftp.encoding = 'utf-8'
            ftp.connect(host=host, port=port)
            ftp.login(user, password)
            hint00.config(text='登录成功，正在删除冗余')

            FindRedundantFiles(ftp=ftp, LocalFolder=saveFolder, ftpFloder=ftpFolder) # 找出本地端多余的文件
            print(str(len(redundant)) + ' following files are redundant:\n', redundant)
            
            # 删除本地多余的文件
            DeleteFileList(redundant)
            redundant = []

            # 延迟，让提示显示一会儿
            window.update()
            window.after(600)
            hint00.config(text='')

            ftp.quit()
        except:
            print('操作失败或操作失败或登录不成功，请核对端口、主机名、用户名以及密码')
            hint00.config(text='操作失败或登录不成功，请核对端口、主机名、用户名以及密码')
            # 延迟，让提示显示一会儿
            window.update()
            window.after(600)
            hint00.config(text='')
    ################################ 更新按钮 ###################################
    apply_btn = tk.Button(window, text='更新本地文件夹', width=20, command=apply, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
    apply_btn.place(x=win_wid / 2 - 80, y=-30+ win_hei / 2 + 115) # 选择放置的位置    
    
    ################################ 删除冗余按钮 ###################################
    delete_btn = tk.Button(window, text='删除所有本地冗余文件', width=20, command=apply2, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
    delete_btn.place(x=win_wid / 2 - 80, y=-30+ win_hei / 2 + 155) # 选择放置的位置    
    ################################################ 鼠标悬浮上空时变色 ########################################
    def on_enter(e):
        apply_btn.config(background='#9999ff')
    def on_leave(e):
        apply_btn.config(background='white')
    apply_btn.bind('<Enter>', on_enter)
    apply_btn.bind('<Leave>', on_leave)

    def on_enter(e):
        delete_btn.config(background='#9999ff')
    def on_leave(e):
        delete_btn.config(background='white')
    delete_btn.bind('<Enter>', on_enter)
    delete_btn.bind('<Leave>', on_leave)

    ################################# 设置一些窗口属性 ###############################
    window.resizable(width=False, height=False)#禁止用户改变窗口大小
    window.mainloop()


if __name__ == '__main__':
    main_window()
    
        
    