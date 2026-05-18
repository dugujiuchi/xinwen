# 长期计划

## 一、正文深度抓取

**当前状态**：News 表已有 `content` 字段，Fetcher 已实现 `fetch_content` 开关和 `content_selector` 配置。API 类源默认开启，浏览器类源默认关闭。

**后续工作**：
- 对浏览器类源逐一测试详情页正文提取，配好 `content_selector`，逐步开启 `fetch_content`
- 列表页本身没有正文的源（如虎嗅），需进入详情页二次抓取
- 正文数据积累后，可接入 AI 摘要/分类/关键词提取

---

## 二、补充数据源（规划/CIM/测绘方向）

现有源偏 AI 科技，资规核心业务方向空白：

| 方向 | 建议源 | 地址 |
|------|--------|------|
| 国土空间规划 | 中国国土空间规划学会 | `http://www.csghs.org.cn/` |
| 规划资讯 | 规划云 | `http://www.guihuayun.com/` |
| CIM/数字孪生 | 城市信息模型CIM网 | `http://www.cim.net.cn/` |
| 测绘地理信息 | 泰伯网GIS频道 | `https://www.taibo.cn/gis` |
| 实景三维 | 自然资源部测绘发展研究中心 | `http://chb.mnr.gov.cn/` |

---

## 三、第三期：关键词匹配数据源

**目标**：用户输入关键词（如"无人机"），系统自动推荐相关数据源。

**实现思路**：
1. Source 表增加 `keywords`、`description` 字段（JSON数组 + 文本）
2. 用户输入关键词 → 后端用 ILIKE 匹配 Source 的 name/description/keywords
3. 匹配结果返回推荐源列表，用户勾选后加入抓取计划
4. 搜索类源（CSDN、机器之心）自动将关键词填入 API 请求参数

---

## 四、用户体系

**当前状态**：管理端用 `.env` 密码做简易鉴权，无用户系统。

**后续按需实施**：
1. User 模型（id/username/password_hash/role）
2. JWT 登录 + token 刷新
3. 角色权限：admin（管理源）/ viewer（只看新闻）/ editor（管理源+审核内容）
4. 管理端 API 替换 `verify_admin` 为 JWT 中间件
5. 用户自定义源与用户关联（`created_by` 字段）
6. 公开页面保持无需登录

---

## 五、AI 能力集成（远期展望）

- 新闻自动摘要（基于 content 字段）
- 新闻自动分类/打标签
- 相关新闻推荐（基于标签/关键词/语义相似度）
- 热点趋势分析
