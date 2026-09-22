__all__=['qwqModule']
#如果一个模块文件中有__all__变量，当使用from xxx import *导入时，只能导入这个列表中的元素;元素是变量，方法，类。
class qwqModule:
    def __init__(self,shit):
        self.shit=shit

    def qwq(self):
        print('here')


def fun():
    print("fun")
abc=12121
if __name__=='__main__':
#所有.py文件中__name__会被自动赋值为__main__；自身作为模块被调用时则会被赋值为.py的文件名。
    fun()
