## 补丁信息路径
资源
- \static\event.css
- \static\event.mp3
- \static\event.png
- \static\event-illustration.jpg
---
前端
- \templates\event\base.html
- \templates\event\contribution.html
- \templates\event\index.html
- \templates\event\login.html
- \templates\event\lottery.html
---
后端
- \web\contributions\
- \web\event.db（后端自动生成）
- \web\event_db.py
- \web\event_web.py
---
启动程序修改
- \main.py

打开main.py添加以下代码：

```import web.event_web```

```app.register_blueprint(web.event_web.bp)```