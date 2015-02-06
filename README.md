#部署在Heroku上
---
俺也是第一次试用Heroku，只是最后发现和我要求的场景**==不那么相符==**，做个记录

Heroku上整个部署流程还是很方便的，下载它的客户端就能很方便的用命令行进行部署操作
部署流程很简单：安装客户端→创建工作目录→heroku create创建APP环境→git push heroku master
嗯，这特喵算是十分理想的流程了。
###几个需要注意的地方
+ 使用heroku create后会自动给git版本管理添加名为heroku的远程仓库，如果该工作目录没有git管理，那么需要自己添加
+ 创建后仅仅是创建，不会运行的，`heroku ps:scale worker=1` == 这样才会运行 ==
+ 每次push任何代码都会自动重新运行，不用显示指定重新启动，也没办法让它不重启
+ 使用heroku某些命令的时候会出现请求错误，按照[https://gist.github.com/fnichol/86750](https://gist.github.com/fnichol/867550/)修复
+ 请使用VPN代理，否则速度会让你抓狂，[**设置gem proxy**](http://stackoverflow.com/questions/3877055/how-to-use-bundler-behind-a-proxy)也是一个不错的选择(搭配shadowsocks的http://localhost:8123)

---
###在谈谈坑吧
+ 最忍受不了的是*重启机制*,本来我的脚本是打算不间断运行的，结果在heroku上动不动就被重启，push创建新版本的时候重启，修改环境变量会重启，改动扩展插件会重启，当然显式运行restart会重启，最特么受不了的是每天会例行检查给你重启（本来我开始想前面的重启我都能理解，最后一个实在是没法忍受了，所以不爱了）
+ heroku的*文件系统*也坑爹，无法读取和保存文件（被git管理的文件除外），所以我需要保存日志的时候蛋疼的选择了用数据库
+ *数据库*这个还好吧，只是有1W行的限制，连接比较容易，嗯是对比的坑爹的openshift的数据库连接