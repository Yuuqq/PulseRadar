# PulseRadar × Cherry Studio 部署指南 🍒

> **适合人群**：零编程基础的用户
> **客户端**：Cherry Studio（免费开源 GUI 客户端）

---

## 📥 第一步：下载 Cherry Studio

### Windows 用户

访问官网下载：https://cherry-ai.com/
或直接下载：[Cherry-Studio-Windows.exe](https://github.com/kangfenmao/cherry-studio/releases/latest)

### Mac 用户

访问官网下载：https://cherry-ai.com/
或直接下载：[Cherry-Studio-Mac.dmg](https://github.com/kangfenmao/cherry-studio/releases/latest)


---

## 📦 第二步：获取项目代码

为什么需要获取项目代码？

MCP 查询需要采集后的新闻数据，不会读取 GitHub Pages 上发布的 HTML 报告。可按 [本地运行指南](README.md#本地运行) 安装依赖并采集，或在已配置远程存储时用 [MCP 同步工具](README-MCP-FAQ.md#存储同步) 拉取数据。Docker 默认将采集数据写入挂载的 `output/`。

根据你的技术水平，可以选择以下任一方式获取代码：

### 方法一：Git Clone（推荐给技术用户）

如果你熟悉 Git，可以使用以下命令克隆项目：

```bash
git clone https://github.com/Yuuqq/PulseRadar.git
cd PulseRadar
```

**优点**：

- 可以用 `git pull` 更新代码；采集数据需要单独运行采集或同步。

### 方法二：直接下载 ZIP 压缩包（推荐给初学者）


1. **访问 GitHub 项目页面**

   - 项目链接：[Yuuqq/PulseRadar](https://github.com/Yuuqq/PulseRadar)

2. **下载压缩包**

   - 点击绿色的 "Code" 按钮
   - 选择 "Download ZIP"
   - 或直接下载 [master.zip](https://github.com/Yuuqq/PulseRadar/archive/refs/heads/master.zip)


**注意事项**：

- 更新代码时请保留本地的配置和 `output/` 数据。

---

## 🚀 第三步：一键部署 MCP 服务器

### Windows 用户

1. **双击运行**项目文件夹中的 `setup-windows.bat`，如果有问题，就运行 `setup-windows-en.bat`
2. **等待安装完成**
3. **记录显示的配置信息**（命令路径和参数）

### Mac 用户

1. **打开终端**（在启动台搜索"终端"）
2. **拖拽**项目文件夹中的 `setup-mac.sh` 到终端窗口
3. **按回车键**
4. **记录显示的配置信息**

---

## 🔧 第四步：配置 Cherry Studio

### 1. 打开设置

启动 Cherry Studio，点击右上角 ⚙️ **设置** 按钮

### 2. 添加 MCP 服务器

在设置页面找到：**MCP** → 点击 **添加**

### 3. 填写配置（重要！）

根据刚才的安装脚本显示的信息填写

### 4. 保存并启用

- 点击 **保存** 按钮
- 确保 MCP 服务器列表中的开关是 **开启** 状态 ✅

---

## ✅ 第五步：验证是否成功

### 1. 测试连接

在 Cherry Studio 的对话框中输入：

```
帮我爬取最新的新闻
```

或者尝试其他测试命令：

```
搜索最近3天关于"人工智能"的新闻
查找2025年1月的"特斯拉"相关报道
分析"iPhone"的热度趋势
```

**提示**：当你说"最近3天"时，AI会自动计算日期范围并搜索。

### 2. 成功标志

如果配置成功，AI 会：

- ✅ 调用 TrendRadar 工具
- ✅ 返回真实的新闻数据
- ✅ 显示平台、标题、排名等信息


---

## 🎯 进阶配置

### HTTP 模式（可选）

如果需要远程访问或多客户端共享，可以使用 HTTP 模式：

#### Windows

双击运行 `start-http.bat`

#### Mac

```bash
./start-http.sh
```

然后在 Cherry Studio 中配置：

```
类型: streamableHttp
URL: http://localhost:3333/mcp
```
