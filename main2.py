# # 1.编码转换
# a='cat'
# b=a.encode()    #unicode编码c=a.encode('unicode_escape'),无参默认utf-8
# print(a,b,type(a),type(b),type(b.decode()))
# # encode只作用于str,对字符串进行Unicode编码,decode则进行解码；对于不可变变量，改变其属性（值，类型）时，会创建一个新的不可变变量，所以type(a)类型不变。

# #2.深浅拷贝
# import copy
# l1=[1,2,3,[4,5,6]]
# l2=l1
# l3=copy.deepcopy(l1)
# l4=copy.copy(l1)
# print(id(l1),id(l2),id(l3),id(l4),id(l1[3]),id(l2[3]),id(l3[3]),id(l4[3]))

# #3.拆包
# a1,b1=[1,2]
# a2,*b2,c2=(1,2,3,4,5)#*将接收到的元素转化为列表
# d={'a3':1,'b3':2,'c3':3,'d3':4}
# e={'a3':7,'b3':8,'c3':9}
# def func(a3,b3,c3,d3):#参数数量和名称必须和字典高度对应。
#     return a3+b3+c3+d3
# print(func(**d),a1,b1,a2,b2,c2)#**对字典d进行拆包，要求字典key必须为字符串。
# print({**d,**e})#字典合并后者覆盖前者

# #4.__all__，__main__
# from qwqmodule import *
# qwqModule1 = qwqModule(1)
# qwqModule1.qwq()   #print(abc)会报错
# #类似私有继承
# import qwqmodule
# print(qwqmodule.__name__)
# #作为模块：供其他脚本导入并调用里面的函数，类；作为独立脚本：直接运行时执行测试、演示或主程序逻辑。
# from mypackage.pk_module import *
# funcc()
# from mypackage import *
# pk_module.funcc()  #pk_moudle2.funcck()不行
#安包：打开cmd，输入pip install （包名称）；开梯子。

#5.递归
#例子：斐波那契数列1，1，2，3，5，8，13...
#函数表的是f(n)=f(n-1)+f(n-2) n>2 f(2)=1,f(1)=1
# def funt(n):
#     if n<3:
#         return 1
#     return funt(n-1)+funt(n-2)
# print(funt(int(input())))
#汉诺塔
def hanoi(n, src, aux, dst):
    if n == 1:
        print(f"{src} → {dst}")
        return  #返回空值。
    hanoi(n-1, src, dst, aux)
    hanoi(1, src, aux, dst)
    hanoi(n-1, aux, src, dst)
hanoi(int(input()), 'A', 'B', 'C')






