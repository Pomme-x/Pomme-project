---
title: 第五周周末及第六周周报
date: 2026-10-25 20:00:00
type: page
---

## 2026/10/16

### 回顾复习三叶草视频

#### 第一个视频：三叶草二进制招新培训2 - 简单的加密算法

因为已将有些忘了，所以复习一下加深印象

![第2页图片](/images/weekly/w02_1.png)

这个是一个简单的加密，类似于凯撒移位，就是给你输入的每个字符都向后加一，然后与代码中给的进行比较，如果一样则正确

视频中ida伪代码加密

```c
scanf("%s", Str1);
for ( i = 0; i < j_strlen(Str1); ++i )
    ++Str1[i];
if ( !j_strlen(Str1,"gmbh|ZPV`GJOE`JU`IBIB~"))
    printf("you are right!\n");
else
    printf("you are wrong!\n");
```

/\*因为没写全所以没办法直接在语雀里直接运行\*/

现在开始尝试跟着无名侠写解密代码

解密代码

```c
#include <stdio.h>
#include <string.h>
int main()
{
    char Str1[]  = "gmbh|ZPV`GJOE`JU`IBIB~";
    for ( int i = 0; i < strlen(Str1); ++i )
    --Str1[i];
    printf("%s\n", Str1);
    return 0;
}
```

![第3页图片](/images/weekly/w03_2.png)

执行成功，解密完成/\*感觉挺有成就感，虽然是跟着老师讲的，但也是自己跟着一步步做出来的，学进了脑子里\*/

因为以后要用Python写所以再次跟着写一个python的

解密代码

```python
target = bytearray(b'gmbh|ZPV`GJOE`JU`IBIB~')
for i in range (len(target)):
    target[i] -= 1
print(target)
```

我不知道为什么target = bytearray(b'gmbh|ZPV`GJOE`JU`IBIB~')中前面要带一个b，把它去掉试试

![第4页图片](/images/weekly/w04_3.png)

报错了，不知道原因，查了查：Python中的bytearray()不能直接接收普通字符串，字符串要转字节，必须指定编码（比如utf-8）/\*我的vscode总是代码写的对的，运行出来是乱码因为这个我之前弄了好久\*/或者直接传字节串（b"xxx"）

```python
target = bytearray('gmbh|ZPV`GJOE`JU`IBIB~', encoding='utf-8')
for i in range(len(target)):
    target[i] -= 1
print(target.decode('utf-8'))
```

上面的这是另外一种方法/\*指定编码（比如utf-8）\*/

#### 第二个视频：三叶草二进制招新培训3 - 简单的加密算法2

![第4页图片](/images/weekly/w04_4.png)

讲的异或运算，异或出现的频率非常高，它是一个二元运算，这是它的运算符号^。

明文 ^ 密钥 = 密文

密文 ^ 密钥 = 明文

它的逆运算就是本身

视频中ida查查看的伪代码

```c
printf("[5] Hi CTFer,Input  your f1ag:")；
scanf("%s"，str1)；
for(i = 0; i < j_strlen(Str1); ++i
    Strl[i]^= i；
if( !j_strcmp(Str1, Str2))
    printf("you are right!in");
    else
    printf("you are wrong!n")；
return 0;
```

Str2中有一个不可见字符（0x7F）会导致ida中不会将Str2直接识别为字符，所以需要用Str2来表示这一串字符

![第5页图片](/images/weekly/w05_5.png)

将这传数据转换成BYTE列表 /\*我们要对其中的每一个字节进行操作

跟着无名侠尝试写python解密

![第5页图片](/images/weekly/w05_6.png)

一开始输出为一串数字，为改为输出为(UTF-8)格式，修改代码成功

![第6页图片](/images/weekly/w06_7.png)

因为是纯手打可能有点慢，我没有他的那个题只能将它抄下来

![第6页图片](/images/weekly/w06_8.jpeg)

![第7页图片](/images/weekly/w07_9.jpeg)

后面是解密代码

解密

```python
, 0x53, 0x5B, 0x55, 0x68]
for i in range(len(date)):
    date[i] = date[i] ^ i
date = bytes(date)
print(date.decode('utf-8'))
```

![第8页图片](/images/weekly/w08_10.png)

可以运行，但是少了点字符，可能是我抄错了

打代码时候多打了几个修改完成后运行

修改后

```python
for i in range(len(date)):
    date[i] ^= i
date = bytes(date)
print(date.decode('utf-8'))
```

![第8页图片](/images/weekly/w08_11.png)

现在好了

标注/\*字符串以0结尾\*/

#### 今日学习总结（附录）

虽然只看了两个视频，但主要的是将他们融会贯通(我打字较慢，该练)

Python中的bytearray()不能直接接收普通字符串，字符串要转字节，必须指定编码（比如utf-8）

今天学了些简单的加密的解密，如何写一些简单的解密脚本，如果有不会的要活用ai，今日ai只用来查了一个python的报错，还有一个重中之重的是写代码时要仔细，不然总是容易出错

今天在实验室就先学这些，我回宿舍会再做几道题进行巩固

#### 明日目标

因为明天周末，所以可以适当放松，但最起码需要再复习3个视频，并做笔记。抽时间需要做题进行巩固。

## 2026/10/17

### 先做几道题

#### 简单XOR

![第9页图片](/images/weekly/w09_12.png)

发现这道题做过了，做下一道题

![第10页图片](/images/weekly/w10_13.png)

先用DIE查看

![第11页图片](/images/weekly/w11_14.png)

PE32位，控制台程序

![第11页图片](/images/weekly/w11_15.png)

控制台运行，需要输入正确的flag，用IDA打开/\*从程序名字可以看出来这是一道简单的XOR加密\*/

![第12页图片](/images/weekly/w12_16.png)

上面是main函数，有明显的XOR，点开查看

![第13页图片](/images/weekly/w13_17.png)

这个是XOR加密黑盒

写解密代码我不理解为什么vscode要让我

![第13页图片](/images/weekly/w13_18.png)

在plain前加一个\*

XOR

```c
#include <stdio.h>
#include <string.h>
int main()  /*变量名：cipher(密文)，key(密钥)，plain(明文)*/
{
    for (int i = 0; cipher[i] != '\0'; i++) {
        cipher[i] ^= key;
    }
    char *plain = cipher;   /*这里不理解为什么有一个‘*’*/
    printf("解密结果：%s\n", plain);
    return 0;
}
```

查了一下

char \*plain﻿ 里的 ﻿\*﻿ 表示 ﻿plain﻿ 是一个字符指针，它存放字符数组地址。这里：

char cipher[] = "...";

char \*plain = cipher;

plain﻿ 指向 ﻿cipher﻿ 的第一个字符。解密循环已经直接修改了 ﻿cipher﻿ 数组，所以

plain﻿ 指向的内容也就是解密后的字符串，﻿printf("%s", plain)﻿ 会从该地址开始打印字符，直到遇到 ﻿'\0'﻿。

然后运行获得flag

Lit8TF{XOR_1s_3asy_to_OR}

![第14页图片](/images/weekly/w14_19.png)

这些是之前做的，python的不想做（不会）

#### BABBYRE

IDA打开就可以看到

但还是用DIE查看一下

![第15页图片](/images/weekly/w15_20.png)

IDA打开直接就可以看到

![第15页图片](/images/weekly/w15_21.png)

#### 第三题

也比较简单

![第16页图片](/images/weekly/w16_22.png)

![第16页图片](/images/weekly/w16_23.png)

是一个linux elf文件IDA打开就可以看到flag

#### 第四题

说真的我英语真的很差

![第17页图片](/images/weekly/w17_24.png)

![第18页图片](/images/weekly/w18_25.png)

DIE查看程序类型，查看之前猜到是ELF程序

![第19页图片](/images/weekly/w19_26.png)

无壳，用IDA打开查看

![第19页图片](/images/weekly/w19_27.png)

额(⊙﹏⊙)不会下一题

查看wp

![第20页图片](/images/weekly/w20_28.png)

![第20页图片](/images/weekly/w20_29.png)

看不懂怎莫说，等有时间问问学长/\*我就是点了下一题，出现这个，结果不会\*/

#### 第五题

简单的花指令，因为之前做过花指令，应该会比较熟悉

![第21页图片](/images/weekly/w21_30.png)

![第21页图片](/images/weekly/w21_31.png)

这就比较简单了

这是一个互补条件加一个垃圾指令的花指令

去除掉之后main就会出现/\*要定义函数（按P）\*/

![第22页图片](/images/weekly/w22_32.png)

这是一个XOR加密，参照上一个XOR加密写脚本

还是C语言脚本吧，简单点

直接套用上一个，改一些代码根据伪代码

![第23页图片](/images/weekly/w23_33.png)

这是写的第一个，提交flag错误，不知道为啥，问问AI

strlen() 本来就不包含结尾的 '\0'，不需要再减一。 sizeof(cipher) - 1 才需要减一，这两种计算方式要区分。

/\*主要是我写了 - 1之后密文最后一个C没有被解密，所以flag最后会出现一个C而不是s（'C' ^ 0x30 = 's'）经过交换之后，到了倒数第二个位置，漏掉了这次 XOR，之后它又被交换到倒数第二个位置，所以出现了 BytesC}，而不是 Bytess}\*/

修改之后

代码

修改之后

```c
#include <stdio.h>
#include <string.h>
int main()  /*变量名：cipher(密文)，key(密钥)，plain(明文)*/
{
    char cipher[] = "c~scvdzKCEoDEZ[^roDICUMC";   /*IDA中看到的密文*/
    char key = 0x30u;  /*key = 0x30*/
   for (int i = 0; i < strlen(cipher); i++) {
    cipher[i] ^= key;
}
    for (int i = 0; i < strlen(cipher) - 1; i += 2) {
        char temp = cipher[i];
        cipher[i] = cipher[i + 1];
        cipher[i + 1] = temp;
    }
    char *plain = cipher;   /*这里不理解为什么有一个‘*’*/
    printf("解密结果：%s\n", plain);
    return 0;
}
```

获得flag

解密结果：NSSCTF{Just_junk_Bytess}

#### 结语

今天就先到这

![第24页图片](/images/weekly/w24_34.png)

做了8道题，在这里写了5道，那三道忘写了，不想再做一遍都是简单的。明天应抱有更大的热情和动力

附录：

strlen() 本来就不包含结尾的 '\0'，不需要再减一。 sizeof(cipher) - 1 才需要减一，这两种计算方式要区分。

char \*plain﻿ 里的 ﻿\*﻿ 表示 ﻿plain﻿ 是一个字符指针，它存放字符数组地址。这里：

char cipher[] = "...";

char \*plain = cipher;

plain﻿ 指向 ﻿cipher﻿ 的第一个字符。解密循环已经直接修改了 ﻿cipher﻿ 数组，所以

plain﻿ 指向的内容也就是解密后的字符串，﻿printf("%s", plain)﻿ 会从该地址开始打印字符，直到遇到 ﻿'\0'﻿。

然后运行获得flag

## 2026/10/18（10/19进行补充）

### base64

简单来说，Base64编码是一种将二进制数据转换为ASCII字符的技术，为了确保数据在网络上传输时的完整性。Base64通过将每三个字节的数据转换位4个6位的字符，并对不足的数据进行补零处理，使用特定字符集进行编码。编码完成后，如果数据长度不是24位的倍数，会用"="进行填充。解码过程则是编码的逆过程。

Base64编码的设计初衷是为了在数据传输过程中，通过特定的字符集编码方式，确保数据的安全性 和完整性。当原始数据包含无法通过某些媒介传输的二进制字节时，Base64提供了一种字符映射方案，使得这些字节能够转换为可通过文本协议传输的ASCII字符

应用场景

1.

电子邮箱传输：在邮件中传输二进制数据时，如附件或图片。

2.

网页编码 ：将非文本数据嵌入到HTML或CSS中。

3.

编程语言序列化 ：在某些语言中，如Python，用于对象序列化。

4.

数据存储 ：存储不需要二进制处理的数据，如数据库中的文本字段。

Base64编码是数据传输中的一种常用编码格式，主要用于将非ASCII字符的数据转换为ASCII字符集中的字符，这样可以保证数据的兼容性和避免传输过程中的错误。本章将深入探讨Base64编码的原理和步

骤。

原理：Base64编码的核心思想是将二进制数据分成长度为3的块，然后将每块转换成4个字符表示。具体步骤如下：

1.

将原始数据按 3 字节（3×8=24位） 为一组。

2.

将 24 位数据按 6 位 分成 4 组（4×6=24位）。

3.

每组 6 位转换为十进制索引，对应索引表中的字符。

4.

若原数据不足 3 字节，用 0 补齐，再用 = 作为填充符。

![第26页图片](/images/weekly/w26_35.png)

解码的过程：查索引表得到 6 位二进制 → 合并成 8 位字节 → 去掉补位。

py脚本#跟着博客写的里面的备注是我自己的理解

![第27页图片](/images/weekly/w27_36.png)

base64

```python
import base64   #导入Python自带的 base64模块
B64 = input("请输入Base64字符串: ")    #接收用户输入的base64字符串
decoded_data = base64.b64decode(B64)    #对base64字符串进行解码
utf8_decoded_data = decoded_data.decode('utf-8')    #将解码后的数据转换为utf-8
```

编码

```
print("解码后的数据:", utf8_decoded_data)    #输出解码后的数据
```

补零：指在二进制数据序列中添加额外的0位，将其长度调整为满足编码算法要求的形式。编码数据长度必须是3的倍数（因为Base64将每3个字节（24位）的数据转换为4个Base64字符）

突然发现三叶草讲base64，开始听

![第28页图片](/images/weekly/w28_37.png)

遇到没有见过的代码可以通过常量来查找

![第28页图片](/images/weekly/w28_38.png)

![第29页图片](/images/weekly/w29_39.png)

简便点理解，比如PKW这三个字母P（80）K（75）W（87）写成二进制：01010000 01001011 01010111

切成四组，每组6b，010100 000100 101101 010111分别对应U E t X，用脚本检验一下

![第29页图片](/images/weekly/w29_40.png)

没问题

我想一个长点的，比如一个20字节的明文，bit = 20\*8=160，每六个一切，160/6=6余下4bit，加两个0，凑够6bit，总共27组，base64必须是4的整数倍，所以结尾要补一个填充=，/\*我有一个疑问为什么要是6bit一拆，二进制111111转换过来是“/”所以刚好为最后一个63，64对应0~63\*/将上面27个全部转换过来，最后面加一个等号补充，这就是base64编码

写脚本的话，需要先将明文转换为

自定义base64编码，在知道明文和密文的前提下，推编码表：

然后我猜测，一个已知明文和密文，先将明文转为ASCII值，然后转为二进制排列，每6bit一组排列，如果不够进行补0，然后把密文也转为ASCII值，然后转为二进制排列，6bit一组，一一对照进行补充编码表，emm，补充=要去掉

### Base64变表逆向

其基本原理是不变,只是改变了它的索引表，正如变表这个名字说的一样

![第30页图片](/images/weekly/w30_41.png)

这种就是改变了编码表

### RC4

RC4不是分组密码，是流密码，是根据密钥生成一串伪随机字节，称为密钥流，再把密钥流与明文逐字节异或

即

密文 = 明文 XOR 密钥流

明文 = 密文 XOR 密钥流

RC4是一个对等算法，加密的本身就是它的解密，所以解密就可以在同样的代码里进行解密

只需要进行修改它的输入和输出

RC4加密

```c
#include <stdio.h>
#include <string.h>
int main(void)
{
    unsigned char key[] = "key";
    unsigned char input[] = "Plaintext";
    unsigned char output[sizeof(input) - 1];
    int key_len = (int)strlen((char *)key);
    int len = (int)sizeof(input) - 1;
    unsigned char S[256];
    int i, j, n;
    unsigned char temp;
    for (i = 0; i < 256; i++)
        S[i] = (unsigned char)i;
    j = 0;
    for (i = 0; i < 256; i++) {
        j = (j + S[i] + key[i % key_len]) & 0xff;
        temp = S[i];
        S[i] = S[j];
        S[j] = temp;
    }
    i = 0;
    j = 0;
    for (n = 0; n < len; n++) {
        i = (i + 1) & 0xff;
        j = (j + S[i]) & 0xff;
        temp = S[i];
        S[i] = S[j];
        S[j] = temp;
        output[n] = input[n] ^ S[(S[i] + S[j]) & 0xff];
    }
    for (n = 0; n < len; n++)
        printf("%02X", output[n]);
    printf("\n");
    return 0;
}
```

对应的解密

对应的解密

```c
#include <stdio.h>
#include <string.h>
int main(void)
{
    unsigned char key[] = "key";
    unsigned char input[] = {
        0x5B, 0x00, 0x55, 0x84, 0x4A,
        0xFB, 0x1E, 0x32, 0x3C
    };
    unsigned char output[sizeof(input)];
    int key_len = (int)strlen((char *)key);
    int len = (int)sizeof(input);
    unsigned char S[256];
    unsigned char temp;
    int i, j, n;
    for (i = 0; i < 256; i++)
        S[i] = (unsigned char)i;
    j = 0;
    for (i = 0; i < 256; i++) {
        j = (j + S[i] + key[i % key_len]) & 0xff;
        temp = S[i];
        S[i] = S[j];
        S[j] = temp;
    }
    i = 0;
    j = 0;
    for (n = 0; n < len; n++) {
        i = (i + 1) & 0xff;
        j = (j + S[i]) & 0xff;
        temp = S[i];
        S[i] = S[j];
        S[j] = temp;
        output[n] = input[n] ^ S[(S[i] + S[j]) & 0xff];
    }
    /* 若明文是文本，按字符串输出 */
    printf("%.*s\n", len, output);
```

```
    return 0;
}
```

### TEA家族（10/22）

#### TEA

分组大小64bit（2个字），密钥128bit（4个字）进行加密32轮，密钥固定按从头到尾进行即k0-&gt;k3存在的缺陷：

1.

等价密钥：TEA名义上有2¹²⁸个密钥，实际上每4个密钥加密效果完全一样

有效密钥只有

2¹²⁶。（k0/k1和k2/k3有对称性质）

2.

密钥表太规律：每轮用的都是相同的k0 k1 k2 k3

TEA加密

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define DELTA  0x9E3779B9u
#define ROUNDS 32
void tea_encrypt(uint32_t v[2], const uint32_t k[4])
{
    uint32_t v0 = v[0], v1 = v[1];
    uint32_t sum = 0;
    for (int i = 0; i < ROUNDS; i++) {
    }
    v[0] = v0;
    v[1] = v1;
}
int main(void)
{
    int len    = (int)strlen(msg);
    for (int i = 0; i < blocks; i++) {
        int n = len - i * 8;                 /* 这一块还剩几个字节 */
        if (n > 8) n = 8;
        memcpy(v, msg + i * 8, n);           /* 只拷实际存在的字节 */
        tea_encrypt(v, key);
        printf("第 %d 块密文: %08X %08X\n", i + 1, v[0], v[1]);
```

```
    }
    return 0;
}
```

我让DSH生成的加密代码

解密过程就是将它倒推

首先第11行sum = DELTA \* ROUNDS（加密时，是正着，这一行是让它从终点出发）

TEA为对称加密，密钥必须一模一样，所以

```c
uint32_t key[4] = {0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210};
```

加密时解出来

![第36页图片](/images/weekly/w36_42.png)

```c
uint32_t cipher[3][2] = {
    {0x047C51F7, 0x8AABF213},
    {0x84DE4A65, 0x7515C91C},
    {0xA6E279E6, 0xE64E1A34},
};
```

密文是按块存放，所以有3块

int blocks = 3;

解密

解密

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#define DELTA  0x9E3779B9u
#define ROUNDS 32
void tea_decrypt(uint32_t v[2], const uint32_t k[4])
{
    uint32_t v0 = v[0], v1 = v[1];
    }
    v[0] = v0;
    v[1] = v1;
}
int main(void)
{
    uint32_t cipher[3][2] = {
        {0x047C51F7, 0x8AABF213},
        {0x84DE4A65, 0x7515C91C},
        {0xA6E279E6, 0xE64E1A34},
    };
    int blocks = 3;                             /*有3块*/
    for (int i = 0; i < blocks; i++) {
        uint32_t v[2] = {cipher[i][0], cipher[i][1]};
        tea_decrypt(v, key);                    /* 解密这一块 */
```

```
    out[24] = '\0';                             /* 补字符串结尾 */
}
```

#### BlockTEA

分组大小变大， 密钥128bit（4个字）加密长度与其长度有关，可以被明文攻击破解

#### XTEA

分组大小64bit（2个字），密钥128bit（4个字）进行加密32轮（64个半轮），与TEA区别，没有规律性，不存在等价密钥

不再使用固定k0~k3，而使用sum的值动态挑一个密钥字

#### XXTEA

分组大小变长（n&gt;=2个字），密钥128bit（4个字）加密轮数为6 + 52/n，整段数据连锁加密

不再8字节为一组，而是把整条消息当成一个大整体，让每个字都受前后字影响

## 2026/10/19

### IDA动态调试

![第39页图片](/images/weekly/w39_43.png)

视频中有一个函数qmemcpy是内存复制

![第39页图片](/images/weekly/w39_44.png)

将第二个参数所对应的值复制28个字节到Str1参数中

![第40页图片](/images/weekly/w40_45.png)

存在一些不可见字符，最后以0结尾

![第40页图片](/images/weekly/w40_46.png)

Str1在代码中不依赖任何输入即无论输入的是什么，最后输入的东西都会在这里与Str1进行比较，Str1是经过代码计算出来的，所以想要查看最后进行比较的是什么，就需要在代码运行到这一行时，查看内存，所以需要在这一行进行下断点，或者在前一行下断点，然后动态调试，F9运行到断点这一行代码F8

单步运行到这一行，然后查看解密后在内存中存了什么

/\*IDA右侧是寄存器窗口，底部是内存窗

口，底部右侧是栈窗口\*/

#### IDA动态调试秒RC4

DIE查看程序结构

![第41页图片](/images/weekly/w41_47.png)

PE32程序，无壳，C语言编写，用ida打开

找到main函数并进入

![第42页图片](/images/weekly/w42_48.png)

将一些未知函数改为熟悉的

![第43页图片](/images/weekly/w43_49.png)

尝试进行动态调试

![第43页图片](/images/weekly/w43_50.png)

有一个反调试，视频中讲，需要绕过这个反调试，先在计算机上运行程序

![第43页图片](/images/weekly/w43_51.png)

![第44页图片](/images/weekly/w44_52.png)

找到正在运行的程序，然后将这个正在运行的程序附属到ida中/\*我的理解，就是这个反调试程序在（printf("Welcome!! give me your flag:\n");）之前，而当程序运行到这里时，再将它附属到ida中则ida会直接在这一行进行，则不会卡在那个反调试处，看到输出的东西说明反调试已经过了\*/

![第44页图片](/images/weekly/w44_53.png)

先分析伪代码（if ( (char)v7[n44_1] == Str[n44_1] )）这是一个if语句，就是当这两个数据相等时，则会进行输出you are right！  所以它的上面第84行就是他的加密，我们在前一行第83行下断点然后动调输入：11111111111111111111111111111111111111111111（44个1）

![第44页图片](/images/weekly/w44_54.png)

断点命中，

![第45页图片](/images/weekly/w45_55.png)

查看一下输入的数据，F8单步运行，（00CFF148）

![第45页图片](/images/weekly/w45_56.png)

我的ida没有加载插件正在解决

解决了

继续

经过加密后11111111111111111111111111111111111111111111（44个1）-

&gt;7DB6A7C7741F7EF97D8DF3295498D5E9B4B8895B620FC958902BD01E431A94C78A253280FD 61950893EBA600

v7=E415C4EDA62F5610BB13EBAD7556C7BBBBE9B9CC023A509F369069BE7C4244CAC6D4245 CD2B924C11893B3EACC给他经过加密会变成明文

再次运行程序动调，

![第46页图片](/images/weekly/w46_57.png)

将这些改为v7

。。。又一个插件没启用，做不成了，让ai给我搞一下

![第46页图片](/images/weekly/w46_58.png)

已疯

![第47页图片](/images/weekly/w47_59.png)

直接用python改

data=bytes.fromhex("E415C4EDA62F5610BB13EBAD7556C7BBBBE9B9CC023A509F369069BE7 C4244CAC6D4245CD2B924C11893B3EACC"); n=ida_dbg.write_dbg_memory(0x0098F704,data); ida_dbg.invalidate_dbgmem_contents(0x0098F72F,len(data));

修改完之后F8单步，查看Str

![第47页图片](/images/weekly/w47_60.png)

![第48页图片](/images/weekly/w48_61.png)

flag出来了/\*已被IDA急哭\*/

## 2026/10/22（10/20修复IDA插件问题，下坏了，重新下的byte老师的 10/21写作业，太多了，作文，英语测试）

### IDA代码修复与数组识别(看不太懂)

IDA按F5反汇编出来的伪代码是IDAS自己猜出来的，并不准确，所以它猜错的地方需要人为进行修改

#### 代码修复：常见问题与对应的处理办法

| 症状 | 处理办法 | 操作 |
| --- | --- | --- |
| 变量类型不对 | 改变量类型 | 光标放变量上按Y |
| 结构体被拆成\*（ a1+a4）\* ( a1+8) | 定义 struct 把参数类型改成结构体指针 | LocalTypes/Structures窗口→Y |
| 参数个数/类型不对 | 改函数原型 | 光标放函数名上按Y 写int fastcallcheck( chaar\*s) |
| 相邻的 XX其实是数组var | 定义数组 | 按\*填长度；或Y直接写intt v[10] |
| 数据被当成代码 | 取消定义后重新定义 | 先U（取消） 再C（代码）或D（数据）或A（字符串） |
| 函数边界错 多出 段尾块、 一 | 重划边界 | Edit>Functions>Setfunction end/Removefunctiontail |
| call analysis failed | 调用约定错 | 右键 call指令→Forcecall type 或改函数原型 |
| sp-analysis failed | 栈失衡 | Alt+K打开栈帧手动改；初学者直接以汇编为准 别花时间强行修复 |

我听得并不太懂，虽然知道如何做但我不知道如何分析

#### 必须记熟的快捷键

| 键 | 作用 |
| --- | --- |
| F5 / Tab | 反编译 / 汇编 <-->伪代码切换 |
| N | 重命名（最高频） |
| Y | 设置类型（第二高频） |
| \* | 定义数组 |
| X | 交叉引用（谁调用/引用了它） 逆向最重要的键—— |
| G / Esc | 跳转地址 / 回退 |
| C / D / A / U | 代码 / 数据 / 字符串 / 取消定义 |
| P / Alt+P | 创建函数 / 编辑函数 |
| Ctrl+K | 栈帧窗口（看局部变量布局） |
| ; | 加注释 |
| Shift+F12 | 字符串窗口（找突破口的第 步）一 |

## 2026/10/23

### [NISACTF 2022]string

比较简单，是只要长度正确，就会输出flag

DIE打开时ELF文件，采用IDA动态调试

![第50页图片](/images/weekly/w50_62.png)

IDA

![第50页图片](/images/weekly/w50_63.png)

写一个简单的脚本

```c
#include <stdio.h>
#include <string.h>
int main() {
    int n13 = 13;
    n13 ^= 0x1Au;
    printf("Result: %d\n", n13);
    return 0;
}
```

就OK了。输入23位

![第51页图片](/images/weekly/w51_64.png)

## 2026/10/24~25

脖子落枕了这两天学的比较少

主要还是进行极客大挑战

我只做了Re的题

wp还没写
