#include <cstdlib>
#include <iostream>

int main() {
    std::cout << "正在移除隔离标记，请输入开机密码：" << std::endl;
    int ret = system("sudo xattr -cr \"/Applications/QRCode Gen.app\"");
    if (ret == 0) {
        std::cout << "完成！现在可以直接双击打开 QRCode Gen.app 了。" << std::endl;
    } else {
        std::cout << "出错了，请确认 QRCode Gen.app 已放入 /Applications 文件夹。" << std::endl;
    }
    return ret;
}
