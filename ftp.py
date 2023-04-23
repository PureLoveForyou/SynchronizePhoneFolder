from datetime import datetime
from ftplib import FTP
from genericpath import isfile
from dateutil import parser
import os
import time
import send2trash

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

# def DeleteFileList(FileList):
#     for file in FileList:
#         if os.path.isfile(file):
#             os.remove(file)
#         else:
#             os.removedirs(file)
#     if len(FileList) >= 1:
#         print('All redundant files deleted')

if __name__ == '__main__':
    # 连接ftp
    ftp = FTP()
    host = '192.168.137.177'
    ftp.encoding = 'utf-8'
    ftp.connect(host=host, port=3721)
    try:
        ftp.login('BravoDesmond', '57474741hjb,')
        rootFolder = '我的文件/' # ftp服务器端的读取的路径
        savedir = './save/' # 保存到本机的路径
        
        SyncFolder(ftp=ftp, rootFolder=rootFolder, savedir=savedir) # 同步文件夹
        FindRedundantFiles(ftp=ftp, LocalFolder=savedir, ftpFloder=rootFolder) # 找出本地端多余的文件

        print(str(len(update)) + ' following files were updated:\n', update)
        print(str(len(error)) + ' following files failed to fetch:\n', error)
        print(str(len(redundant)) + ' following files are redundant:\n', redundant)

        # # 删除本地多余的文件
        DeleteFileList(redundant)

        ftp.quit()
    except:
        print('操作失败或登录不成功，请核对端口、主机名、用户名以及密码')