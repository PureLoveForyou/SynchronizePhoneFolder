from datetime import datetime
from ftplib import FTP
from dateutil import parser
import os
import time
import tkinter as tk
from tkinter import END, ttk
import send2trash
from PIL import Image, ImageTk
from tkinter.filedialog import askdirectory

# from progressbar import ProgressBar,Percentage,Bar,ETA,FileTransferSpeed

update = [] # 记录更新的文件
error = [] # 记录复制失败的文件
redundant = [] # 记录本机比服务器多的文件


# # 从ftp服务器段下载文件(控制台显示进度条)
# def getFile(ftp, rootFolder, filename, savedir):
#     file = open(savedir+filename, 'wb')
#     file_size = ftp.size(rootFolder + filename)

#     widgets = ['Downloading: ', Percentage(), ' ',
#                     Bar(marker='#',left='[',right=']'),
#                     ' ', ETA(), ' ', FileTransferSpeed()]
#     pbar = ProgressBar(widgets=widgets, maxval=file_size)
#     pbar.start()

#     def file_write(data):
#         file.write(data) 
#         nonlocal pbar
#         pbar += len(data)

#     # try:
#     ftp.retrbinary("RETR " + rootFolder + filename, file_write)
#     file.close()
#     pbar.update()
#     pbar.finish()
#     # except:
#     #     print("Error! " + savedir+filename)
#     #     error.append(savedir+filename)


# 从ftp服务器段下载文件(tkinter显示进度条)
def getFile(ftp, rootFolder, filename, savedir, window, pbar):
    file = open(savedir+filename, 'wb')
    file_size = ftp.size(rootFolder + filename)
    pbar['maximum'] = file_size
    pbar['value'] = 0

    def file_write(data):
        file.write(data) 
        nonlocal pbar,window
        window.update()
        pbar['value'] += len(data)

    try:
        ftp.retrbinary("RETR " + rootFolder + filename, file_write)

    except:
        print("Error! " + savedir+filename)
        error.append(savedir+filename)
    file.close()


# 简单判断是文件夹还是文件名
def isdir(filaname):
    content = filaname.split('.')
    if len(content) == 1:
        return True
    return False

# 同步文件夹，以及子文件夹（服务器有，但本地没有的文件会被复制；服务器有，且本地也有的文件，根据时间戳判断是否需要更新；但是本地有，而服务器没有的文件，此函数不会删除本地的这种文件）
# def SyncFolder(ftp, rootFolder, savedir):
def SyncFolder(ftp, rootFolder, savedir, hint, window, pbar, pbar2):
    lines = []
    ftp.dir(rootFolder, lines.append) # 获取文件名以及时间戳
    pbar2['maximum'] += len(lines)
    for line in lines:
        pbar2['value'] += 1

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
                
                window.update()
                # window.after(600)
                hint.config(text='正在同步文件'+str(pbar2['value'])+'/'+str(pbar2['maximum'])+':'+rootFolder+filename)
                update.append({savedir+filename,source_time})
                # getFile(ftp, rootFolder, filename, savedir) # 服务器文件修改过才更新
                
                getFile(ftp, rootFolder, filename, savedir, window=window, pbar=pbar) # 服务器文件修改过才更新
        else:
        # 是文件夹，进入该文件夹，然后递归调用
            if not os.path.isdir(savedir+filename):
                os.mkdir(savedir+filename+'/') # 在本机创建不存在的文件夹
            # SyncFolder(ftp, rootFolder=rootFolder + filename + '/', savedir=savedir+filename+'/')
            SyncFolder(ftp, rootFolder=rootFolder + filename + '/', savedir=savedir+filename+'/', hint=hint, window=window, pbar=pbar, pbar2=pbar2)
        
# 本地有，而服务器没有的文件，此函数将记录这种文件及其路径，方便后面决定是否删除
# def FindRedundantFiles(ftp, LocalFolder, ftpFloder):
def FindRedundantFiles(ftp, LocalFolder, ftpFloder,pbar2,window):
    # pbar是单个文件进度，pbar2是全部进度
    filenames = os.listdir(LocalFolder) # 列出所有文件
    pbar2['maximum'] += len(filenames)
    for filename in filenames:
        pbar2['value'] += 1
        window.update()
        if filename not in ftp.nlst(ftpFloder):
            # print('file redundant: ', LocalFolder+filename) 
            redundant.append(LocalFolder+filename)# 不在ftp服务器的就是多余的
        else:
            if os.path.isdir(LocalFolder+filename): # 在服务器中，但是是文件夹的，递归进入文件夹寻找
                # FindRedundantFiles(ftp, LocalFolder=LocalFolder+filename+'/', ftpFloder=ftpFloder+filename+'/')
                FindRedundantFiles(ftp, LocalFolder=LocalFolder+filename+'/', ftpFloder=ftpFloder+filename+'/', pbar2=pbar2, window=window)

def DeleteFileList(FileList,pbar2,window):
    length = len(FileList)
    # for file in FileList:
    pbar2['maximum'] += length
    while FileList != []:
        file = FileList.pop()
        pbar2['value'] += 1
        window.update()
        if os.path.isfile(file):
            # os.remove(file) # 风险太大
            send2trash.send2trash(file)# 回收站比较保险
        else:
            if not len(os.listdir(file)):
                # os.removedirs(file) # 空文件夹就删除, 风险太大
                send2trash.send2trash(file)# 空文件夹放入回收站，回收站比较保险
            else: # 非空文件夹，列举出其中的文件递归
                newlist = [file + '/' + x for x in os.listdir(file)]
                DeleteFileList(newlist,pbar2=pbar2,window=window)
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
    

    # 声名全局变量
    window = tk.Tk()
    window.title("FtpSync") # window title
    window.geometry("400x480") # window size
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
    input_hint.place(x=length1-14, y=-80+win_hei / 2 - 40) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_host = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_host.place(x=length1 - 8 + input_hint.winfo_width(), y=-80+win_hei / 2-39) # 选择放置的位置
    input_entry_host.insert(0, host)
    # 操作提示框
    hint00 = tk.Label(window, text='', bg='white', font=('微软雅黑', 12),wraplength=win_wid)
    hint00.pack(side='bottom')

    ################################# Port输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='Port:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1-12, y=-80+win_hei / 2 - 15) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_port = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_port.place(x=length1 - 5 + input_hint.winfo_width(), y=-80+win_hei / 2 - 15) # 选择放置的位置
    input_entry_port.insert(0, port)

    ################################# UserName输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='User:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 12, y=-80+win_hei / 2+10) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_user = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_user.place(x=length1 - 7 + input_hint.winfo_width(), y=-80+win_hei / 2 +10) # 选择放置的位置
    input_entry_user.insert(0, user)
    ################################# Password输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='Password:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1-50, y=-80+win_hei / 2 + 35) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_password = tk.Entry(window, font=('微软雅黑', 12), width=18, show='*') # show='*'使得输入的字符全部显示为'*'
    input_entry_password.place(x=length1 - 45 + input_hint.winfo_width(), y=-80+win_hei / 2 + 35) # 选择放置的位置
    input_entry_password.insert(0, password)
    ################################# ftpFolder输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='ftpFloder:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 48, y=-80+win_hei / 2+60) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_ftpFolder = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_ftpFolder.place(x=length1 - 43 + input_hint.winfo_width(), y=-80+win_hei / 2 +60) # 选择放置的位置
    input_entry_ftpFolder.insert(0,ftpFolder)
    ################################# UserName输入框提示和输入框 ###############################
    # 定义输入框的提示文字
    input_hint = tk.Label(window, text='SaveFloder:', bg='white', font=('微软雅黑', 12))
    input_hint.place(x=length1 - 61, y=-80+win_hei / 2+85) # 选择放置的位置
    input_hint.update()
    # 定义输入框
    input_entry_saveFolder = tk.Entry(window, font=('微软雅黑', 12), width=18) # show='*'使得输入的字符全部显示为'*'
    input_entry_saveFolder.place(x=length1 - 56 + input_hint.winfo_width(), y=-80+win_hei / 2 +85) # 选择放置的位置
    input_entry_saveFolder.insert(0, saveFolder)

    # 定义进度条（全部文件总进度）
    pbar2 = ttk.Progressbar(window, orient='horizontal', length=100)
    pbar2.pack()
    
    # 单个文件的进度条
    length_tmp = 170
    pbar = ttk.Progressbar(window, orient='horizontal', length=length_tmp)
    pbar.place(x=win_wid/2 - length_tmp/2 + 5, y=win_hei-80)
    # pbar2.pack()
    
    # 看手动输入的路径是否存在
    if not os.path.isdir(saveFolder[:-1]):
        try:
            os.mkdir(saveFolder)
        except:
            hint00.config(text='保存路径不合法或为空，请检查')
    
    def apply():
        host = input_entry_host.get()
        port = int(input_entry_port.get())
        user = input_entry_user.get()
        password = input_entry_password.get()
        ftpFolder = input_entry_ftpFolder.get()
        saveFolder = input_entry_saveFolder.get()
        writeconfig(port=port, host=host,user=user,password=password,saveFolder=saveFolder,ftpFolder=ftpFolder)
        try:
            window.update()
            hint00.config(text='连接ftp服务器中：ftp://{host}:{port}'.format(host=host,port=port))

            # 连接ftp
            ftp = FTP()
            ftp.encoding = 'utf-8'
            hint00.config(text='尝试连接和登录')
            window.update()
            ftp.connect(host=host, port=port,timeout=2)
            ftp.login(user, password)
            hint00.config(text='登录成功，正在同步')
            window.update()
            
            # SyncFolder(ftp=ftp, rootFolder=ftpFolder, savedir=saveFolder) # 同步文件夹
            # tmp = []
            # ftp.dir(ftpFolder, tmp.append) # 获取文件名以及时间戳
            pbar2['maximum'] = 0
            pbar2['value'] = 0
            SyncFolder(ftp=ftp, rootFolder=ftpFolder, savedir=saveFolder, hint=hint00, window=window, pbar=pbar, pbar2=pbar2) # 同步文件夹
            # FindRedundantFiles(ftp=ftp, LocalFolder=saveFolder, ftpFloder=ftpFolder) # 找出本地端多余的文件

            print(str(len(update)) + ' following files were updated:\n', update)
            print(str(len(error)) + ' following files failed to fetch:\n', error)
            # print(str(len(redundant)) + ' following files are redundant:\n', redundant)
            # 延迟，让提示显示一会儿
            window.update()
            # window.after(600)
            hint00.config(text=str(len(error)) + '个文件同步失败，'+str(len(update))+'个文件更新',wraplength=win_wid*7/8)

            ftp.quit()
        except:
            print('操作失败或登录超时，请核对路径以及端口、主机名、用户名以及密码')
            hint00.config(text='操作失败或登录超时，请核对路径以及端口、主机名、用户名以及密码')
            # 延迟，让提示显示一会儿
            window.update()
            # window.after(990)
            # hint00.config(text='')
    
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
            hint00.config(text='尝试连接和登录')
            window.update()
            ftp.connect(host=host, port=port,timeout=2)
            ftp.login(user, password)
            hint00.config(text='登录成功，正在检测冗余，可能会有遗漏，建议多次检测')

            redundant.clear()
            # FindRedundantFiles(ftp=ftp, LocalFolder=saveFolder, ftpFloder=ftpFolder) # 找出本地端多余的文件
            pbar2['maximum'] = 0
            pbar2['value'] = 0
            FindRedundantFiles(ftp=ftp, LocalFolder=saveFolder, ftpFloder=ftpFolder, pbar2=pbar2,window=window) # 找出本地端多余的文件
            print(str(len(redundant)) + ' following files are redundant:\n', redundant)
            
            # 弹出提示窗口
            warning_window = tk.Tk()
            warning_window.title("移入回收站提示") # window title
            warning_window.geometry("800x300") # window size
            warning_window.config(bg='white')
            warning_window.update() # 不更新的话得到的宽高是1
            warn_win_hei = warning_window.winfo_height()
            warn_win_wid = warning_window.winfo_width()
            # 定义新密码输入框的提示文字
            warn_hint = tk.Label(warning_window, text='这会删除此电脑“'+ saveFolder +'”路径下与ftp服务器路径：“ftp:/'+ftpFolder+'”不一致的文件，删除的文件可在回收站中找到，确定要继续吗？', bg='white', font=('微软雅黑', 12),wraplength=warn_win_wid*9/10)
            warn_hint.place(x=length1-56, y=warn_win_hei / 2 - 80) # 选择放置的位置
            warn_hint2 = tk.Label(warning_window, text='\n将要删除'+str(len(redundant))+'个文件，如'+str(redundant[:])+'等', bg='white', font=('微软雅黑', 12), wraplength=warn_win_wid*4/5)
            warn_hint2.place(x=length1, y=warn_win_hei*3 / 5) # 选择放置的位置
            # 确定按钮，锁屏并更改状态
            def sure():
                warning_window.destroy() # 退出提示窗口
                global redundant
                tmp = len(redundant)
                pbar2['maximum'] = 0
                pbar2['value'] = 0
                # 删除本地多余的文件
                DeleteFileList(redundant, pbar2=pbar2,window=window)
                redundant = []

                # 延迟，让提示显示一会儿
                window.update()
                # window.after(600)
                hint00.config(text=str(tmp)+'个文件移入回收站成功')

            sure_btn = tk.Button(warning_window, text='确定', width=20, command=sure, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
            sure_btn.place(x=warn_win_wid / 5, y = warn_win_hei / 2) # 选择放置的位置 
            # 获取输入框的文本
            def cancel2():
                warning_window.destroy() # 退出程序

            # 取消设置的按钮
            cancel_btn2 = tk.Button(warning_window, text='取消', width=20, command=cancel2, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
            cancel_btn2.place(x=warn_win_wid*3 / 5, y = warn_win_hei / 2) # 选择放置的位置
            # 悬浮颜色提示
            def on_enter(e):
                sure_btn.config(background='#9999ff')
            def on_leave(e):
                sure_btn.config(background='white')
            sure_btn.bind('<Enter>', on_enter)
            sure_btn.bind('<Leave>', on_leave)
            def on_enter(e):
                cancel_btn2.config(background='#9999ff')
            def on_leave(e):
                cancel_btn2.config(background='white')
            cancel_btn2.bind('<Enter>', on_enter)
            cancel_btn2.bind('<Leave>', on_leave)
            
            ftp.quit()       
        except:
            print('操作失败或登录超时，请核对路径以及端口、主机名、用户名以及密码')
            hint00.config(text='操作失败或登录超时，请核对路径以及端口、主机名、用户名以及密码')
            # 延迟，让提示显示一会儿
            window.update()
            # window.after(990)
            # hint00.config(text='')

    def directory():
        # get a directory path by user
        nonlocal saveFolder
        input_entry_saveFolder.delete(0,END)
        saveFolder=askdirectory(initialdir=r"C:\Documents\Code\Python\SyncPhoneFolder\GenerateExe\dist\save",
                                        title="Dialog box")
        if saveFolder[-1] != '' and saveFolder[-1] != '\\' and saveFolder[-1] != '/':
            input_entry_saveFolder.insert(0,saveFolder+'/')
        else:
            input_entry_saveFolder.insert(0,saveFolder)
    ################################ 更新按钮 ###################################
    apply_btn = tk.Button(window, text='更新本地文件夹', width=20, command=apply, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
    apply_btn.place(x=win_wid / 2 - 80, y=-30+ win_hei / 2 + 115) # 选择放置的位置    
    
    ################################ 删除冗余按钮 ###################################
    delete_btn = tk.Button(window, text='删除所有本地冗余文件', width=20, command=apply2, bg='white', font=('微软雅黑', 10)) # 只有通过这个退出按钮才可以退出程序
    delete_btn.place(x=win_wid / 2 - 80, y=-30+ win_hei / 2 + 155) # 选择放置的位置    

    ################################### 选择文件夹按钮 #######################################################
    dialog_btn = tk.Button(window, text='选择保存位置', width=20, background='white', font=('微软雅黑', 10),command = directory)
    dialog_btn.place(x=win_wid / 2 - 80, y=-30+ win_hei / 2 + 75) # 选择放置的位置  

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

    def on_enter(e):
        dialog_btn.config(background='#9999ff')
    def on_leave(e):
        dialog_btn.config(background='white')
    dialog_btn.bind('<Enter>', on_enter)
    dialog_btn.bind('<Leave>', on_leave)

    ################################# 设置一些窗口属性 ###############################
    window.resizable(width=False, height=False)#禁止用户改变窗口大小
    window.mainloop()


if __name__ == '__main__':
    main_window()
    
        
    