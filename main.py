# #TAB，ctrl+z，ctrl+/,ctrl+函数名
import math
import copy
# from math import sqrt,log
# print(sqrt(4))
# from math import *#不需要使用模块.的形式；调用多模块同名函数时，后覆盖前。
# i=sqrt(4)
# j=log(2,4)
# print(i,j)


# #一.
# print('MOM!'+" DA\n""D!"'let\'s go!')
# #python中'和“是一样的；‘前加\避免歧义；换行用\n。
# print('\n')
# print("""MOM! DA
# D!let's go!""")
# #"""或'''可以替代\n功能。
# print('qwq'+' qwq'+' qwq',' qwq')
# print('qwq','qwq','qwq',1,sep='?')
#,可以输出任何类型，+只能输出同一类型；sep是,分隔开的内容间的连接符，不写则默认空格。
# print('qw\t''w\t''q\n'
# 'q\t''w\t''qw')
# print('q\t''qw\t''q')
#/t制表符，输出时自动使上下对齐

# #二.
# a=math.sqrt(2**4)
# #幂运算符**，引用math函数库函数需要加math.;或者使用pow(2,4)。
# b=1+2-3/4*5
# c=math.sin(math.pi/6)
# #三角函数：三角函数计算采用弧度制圆周率,e等用math.pi,math.e表示。
# d=1^2
# #异或运算符^。
# e="!我的天啊!?"
# f=bool("wdf")
# #bool变量与其他变量运算时，True=1,False=0;bool转化其他变量时0转化为False，其他转化为True
# g=True
# # python中bool,float,int变量间运算可直接运行无需转换
# try:
#     h=int(input())
# except ValueError as e:
#     print(e)
#     print('傻逼')
# # input只接受字符串变量。
# except Exception as e2:
#     print('f5',e2)
# else:
#     print(a,b,c,d,e[0],e[-1],e[1:5:2],len(e),f+1,type(g),g+1,h+1)
# #不同变量输出用,隔开。;len只可用于字符串;bool类型;e[1:5:2]不带步长默认1,不输出结束字符，即包前不包后。
# finally:
#     print('gg')
# for d3 in range(3,12,3):
# #range不包含最后一个数12；最后一个数3为步长；类似列表；(100)表示从1开始到100，步长为1；(2,100)省略步长。
#     while d3<10:
#         d3+=1
#         print(d3)
# g="1211564115954941164549Qa qw jt"
# print(g.lower(),g.startswith('1'),g.title())
# #startswith是否以什么开始，capitalize首字母是否大写，endswith，lower，upper小写转大写，isupper是否全大写。
# print(g.replace('1','9',3),g.split('5',2),g.count("11",5,19))
# #count返回找到的个数;replace中3为替换次数；split返回列表，其中3为分割次数。
# m=0
# while True:
#     m=g.find('11',m,30)  #find寻找从第m个下标开始到第30个下标结束的第一个与11相同的字符的下标,找不到则返回-1.
#     if m== -1:break #跳出循环
#     print(m)
#     m+=1
#     #index与find一样，但找不到会报错。



# #三.
# a1=int(input())
# b1=int(input())
# if a1:
# # if后将变量转换为bool类型，True输出，False不输出。
#     print("1")
#     if b1:
#         print("2")
#     else:
#         print("3")
# else:
#     print("4")
#     print("5")
# print("6")
# #依次执行if1,if2…中间碰到0执行elsen；未缩进独立于if语句之外，一定会输出。
# if a1:
#     print("7")
# elif b1:
#     print("8")
# else:
#     print("9")
# #相当于else if;只执行True的那句，若全为False, 执行else;若多个True, 执行第一个True。
# if a1 and b1:
#     print("10")
# elif a1 or b1:
#     print("11")
# elif not b1:
#     print("12")
# elif a1 or (not (b1 and 0)):
#     print("13")
# a=1
# b=2
# print('a>b' if a > b else 'a<b')
# comp=lambda a,b:'a>b' if a > b else 'a<b'
# print(comp(a,b))
# #相当于def funk():return 'a>b' if a > b else 'a<b'  print(funk())


# #四.(,)元组tuple，[,]列表，{:,:}字典dict,{,}集合set
# a2= ["Qq", '2', '3e',"q","0"]
# a2.sort()    #sorted不改变原始顺序，返回新列表；sort返回排序后原列表
# a2.remove("2")
# a2.append("o")#添加o，默认放最后面
# print(max(a2),sorted(a2),a2[3],a2[0:2],a2)  #依旧包前不包后
# #比较原则:从第一个字母开始比较，按ASCII排行，1-9，A-Z,a-z;不同类型变量间不能相互比较;sorted从小到大排列。
# p5=['a','b','c',11,22,11]
# p5.insert(3,"qwq")   #在第3个位置添加q。
# p5.extend('我的天')  #打散添加。
# p5[0]=5
# print(p5,p5.count(11),p5.index(11,1,5))#同字符串
# del p5[0]  #del p5表示删除列表
# print(p5,p5.pop(0),p5.reverse())  #pop返回删掉的值，不传参默认删掉最后一个。
#print先按顺序内计算，然后再按顺序外输出。
# b2={("shit",1):"1",("shit",2,3):[1,"q"],11:99,1.21:"9"}
# print(b2.values(),b2.keys(),b2.items())
# print(b2[('shit',1)],b2.get(1.21))
# tuple(元组,不可变类型，包容所有变量，不能向里面添加变量)。
# Key可以是int,str,float,tuple,bool;value可以是任意类型。
# 添加键值对b2["qwq"]="5"
# del b2[1.21]
# c2=eval(input())
# #eval函数可去掉“”，恢复原始类型
# if c2 in b2:
# #in函数，如果c2在b2里，返回True,否则False；
#     print(b2[c2],len(b2))
# print(b2.clear())#清空字典内容
# del b2#删掉整个字典
# print(type({}),type(set()))#{}定义空字典，set()定义空集合
# p9={'1','9','8'}
# print(p9,hash('1'),hash('9'),hash('8'))  #str具有无序性，每次运行顺序都不一样;数字一样；哈希值是地址。

# #五
# a3={1:2,3:4,5:6,7:8,9:10}
# for b3 in a3.items():
# # item把键值对变成元组赋值给a,b；in遍历键值对。
# # 也可以用for a,b in a3.items():。
# # 除了item，还有a3.key,a3.value用来遍历接受,.key可省略;列表也可以用来for循环。
#     c3=eval(input())
#     if b3==c3:
#         print(c3)
# e3='{0}{1}{0}'.format('我','是')
# f3='{shit}{gg}{shit}'.format(shit=1,gg=2)
# print(f'{e3}',f'{f3}')
# a='abc'
# print('ab' in a,'ac' not in a)
# #in其他用法

#六
# def area(r2,r=0):#默认参数一定写在非默认参数后面。
#     print(r)
#     a4=r*r
#     print(a4,r2)
#     return area
# area(0)
# area(2)(3)      #链式调用
# def area2(*args):
#     print(args)   #args是元组，args可以是其他参数名，加*就行
# area2(1,2,'3')#空参数是空元组
# def area3(**kwargs):
#     print(kwargs)   #kwargs是字典，kwargs可以是其他参数名，加**就行
# area3(shit=147,we='1997',adw=[1,2,3])   #空参数是空字典；key不同于普通字典，必须是合法参数名，由字母，_，数字组成。
# #python只有引用传递。
# def area5():
#     print('不知道')
#     def aera6():#作用域仅限area5内部，不可在外部被调用。
#         print('我的天')
#     aera6()
# area5()
# a=1 #默认全局变量
# def fun():
#     global a  #函数内会将a修改为局部变量，通过global修改为全局变量。
#     a=0
#     print(a)
# fun()
# print(a)
# def fun2():
#     a=2 #再次修改为局部变量。
#     print(a)
# fun2()
# print(a)
# add=lambda a,b: a+b  #匿名函数相当于def add():return a+b
# print(add(1,2))

# a5=all([True, 1, 'ok']) # 所有元素为真则返回True
# a51=all([True, 0, 'ok'])
# b5=any([False, 0, 1])   # 只要有一个为真则返回True
# b51=any([False, 0, 0])
# print(a5,a51,b5,b51)
# breakpoint()         # 进入断点
# c5=bin(9)              # 转二进制字符串;0b代表二进制，比如0o代表八进制。
# d5=complex(1, 2)        # 创建复数 -> (1+2j)
# e5=sum([1,2,3])     #求和
# f5=round(9.515,2)    #四舍五入并保留几位小数
# g5=abs(-1)              #绝对值
# print(c5,d5,e5,f5,g5,max([1,2]),min(1,-2,key=abs))#取绝对值后再比较，并且返回原值。
# k1=[1,2]
# k2=(3,4,5)
# k3={1:['q',2],3:'s'}
# k4=zip(k1,k2,k3)
# print(k4)
# #打包可迭代对象，将元素按索引一一配对，返回一个包含元组的迭代器；若可迭代对象长度不同，以最短的为准。
# #可迭代对象：含有多个元素的容器，比如str,tuple,list,dict,set，zip
# print(type(k3))
# for k in k4:
#     print(k)
# a,b,c=zip(*k4)       #拆包str,tuple,list,dict也可以用这个
# print(a,b,c)
# #解包，清空zip。
# k5=list(k4)
# print(k5)
# #打包后转列表
# k6=dict(zip(k2,k3))
# print(k6)
# #打包后转字典,必须是两个可迭代对象的zip。
# def fun7(fn):
#     return 2*fn
# k7=map(fun7,[1,2])
# print(type(k7))
# for k in k7:
#     print(k)
# #同样可以转list,dict等。


# #七
# class animal:
#     def __init__(self, sound):
#         self.sound = sound
#     def m1(self,t):
#         print('do '*t)
#     def m2(self,t): #形参，不必担心重名
#         print('make '*t)
# class cat(animal):
#     def __init__(self, age, sound):  #构造函数。
#         super().__init__(sound) #调用父类构造函数；若子类没有自己的构造函数则直接使用父类的，若有则必须super
#         self.age = age
#         print('我的天')
#         self.other={"体重":0,'身高':0}
#     def m3(self,t):
#         print('跳'*t)
#     def m1(self,j):  #同名则直接覆盖父类方法
#         print('notdo '*j)
#         super().m1(2)  # 调用父类方法；不受覆盖影响
#     def putin(self,key,value):
#         if key in self.other:  #同样，.key可省略
#             self.other[key]=value
# cat1=cat(9,'喵')
# cat1.m1(3)
# cat1.m2(3)
# cat1.m3(3)
# cat1.putin('身高',1.2)
# cat1.putin('体重',30)
# print(cat1.other,cat1.sound)

# #八
# with open(r"D:\wenjian\杂项\python.txt", 'r', encoding='utf-8') as p:
#  #r若无此文件会报错
#     print(p.read(2))    #读取1 q
#     print(p.readline())  #读取w q \n
#     print(p.read(3))     #读取2 \n 3
#     print(p.readline())
#     print(p.readline())
# with open(r"D:\wenjian\杂项\python.txt", 'r', encoding='utf-8') as p:
#     lines=p.readlines()  #读取全部内容并创建列表
#     print(lines)
#     for line in lines:
#         print(line)
# with open(r"D:\wenjian\杂项\python2.txt", 'a', encoding='utf-8') as p:
#  #a不会清空文件内容，而是在后面附加；若无此文件会自动创建
#     p.write("\nqwq\n")
#     p.write("kmj")
# with open(r"D:\wenjian\杂项\python3.txt", 'w', encoding='utf-8') as p:
#     #w会清空文件内容；若无此文件会自动创建
#     p.write('kmj\n')
#     p.write('kmj+')
# with open(r"D:\wenjian\杂项\python3.txt", 'r+', encoding='utf-8') as p:
#     #r+可读可写
#     p.write("kmj+")
#     print(p.read())

