# import pysftp

# with pysftp.Connection(host='192.168.137.154', username='bravodesmond', port=2222,password='57474741hjb,') as sftp:
#     print('yes')

#导入paramiko，（导入前需要先在环境里安装该模块）
import paramiko
import os

#定义函数ssh,把操作内容写到函数里
def sshExeCMD():
    #定义一个变量ssh_clint
    ssh_client=paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #使用cnnect类来连接服务器
    ssh_client.connect(hostname="192.168.137.198", port="2222", username="bravodesmond", password="57474741hjb,")
    return ssh_client

import pywintypes, win32file, win32con
def changeFileCreationTime(fname, newtime):
    wintime = pywintypes.Time(newtime)
    winfile = win32file.CreateFile(
        fname, win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None, win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL, None)

    win32file.SetFileTime(winfile, wintime, None, None)
    winfile.close()

#通过判断模块名运行上边函数
if __name__ == '__main__':
    ssh = sshExeCMD()
    sftp = ssh.open_sftp()
    # dirs = sftp.listdir()
    # print(dirs)
    # print(sftp.getcwd())
    # sftp.get('我的文件/sync.txt', r'C:\Users\黄金波\Desktop\sync.txt')
    # sftp.get('DCIM/Camera/IMG_20190627_194113.jpg', r'C:\Users\黄金波\Desktop\IMG_20220204_195301.jpg')
    # sftp.get('DCIM/Jovi Vision IMG/IMG_20220204_195301.jpg', r'C:\Users\黄金波\Desktop\IMG_20220204_195301.jpg')
    # print(sftp.lstat('DCIM/Jovi Vision IMG/IMG_20220204_195301.jpg'))
    
    # t = sftp.stat('DCIM/Camera/IMG_20190627_194113.jpg')
    t = sftp.stat('DCIM/Jovi Vision IMG/IMG_20220204_195301.jpg')
    atime = (t.st_atime)
    mtime = (t.st_mtime)
    
    stinfo = os.stat(r'C:\Users\黄金波\Desktop\IMG_20220204_195301.jpg')
    print(stinfo.st_mtime)
    
    # 改变文件的“修改时间”和“访问时间”
    # atime = 200000000
    # mtime = 200000000
    os.utime(r'C:\Users\黄金波\Desktop\IMG_20220204_195301.jpg',(atime,mtime))
    
    # 修改文件的创建时间
    changeFileCreationTime(r'C:\Users\黄金波\Desktop\IMG_20220204_195301.jpg',mtime)
