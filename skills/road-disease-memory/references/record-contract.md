# 记录协议 v1

## 必填字段

`kind`：inspection（巡检）、sample（病害样本）、diagnosis（诊断依据摘要）、standard（规范引用）、experiment（模型实验）、recommendation（建议）、feedback（养护反馈）。

所有记录必须有 `project`、`title`、`summary`、带时区的 `observed_at`、`review` 和非空 `sources` 数组。每个来源有 `uri` 和 `note`，说明它支持什么事实。来源可以是本地路径、文档页码引用或公开链接，系统不会自动下载链接或验证其内容。

`review` 为 provisional（待核验）、verified（记录者已核验）、rejected（已否定）。创建时间由程序自动保存，区别于事实发生时间。可选 `road`、`diseases` 和 `payload`。数据采用 JSON；未定义的顶层字段拒绝写入，扩展内容放入 payload。

## 实验约束

`payload.model` 保存模型名称；`payload.metrics` 保存数值指标。map50、map50_95、precision、recall 使用 0..1，拒绝 NaN、无穷及百分数误填。

`payload.comparison` 至少含：

- dataset_sha256：实际参与评估的数据清单的 SHA-256，清单应包含各图像/标签内容哈希与划分。仅对文件夹路径做哈希不能证明数据相同。
- classes_sha256：有序类别定义文件的 SHA-256。
- split：实际划分，例如 test-v1，不能混用 validation/test。
- evaluation_protocol：协议标识，对应版本化的评估配置（IoU、置信度、NMS、指标实现与软件版本等）。
- image_size：评估尺寸；额外条件如矩形推理、增强、设备/批次与计时方式也应放入 comparison。所有 comparison 字段精确相等才比较。

例如 `payload` 还可保存超参数、随机种子、轮次、训练数据清单哈希、软件版本、硬件、评价限制。比较是对已有实验的筛选，不声称统计显著性，也不按测试集反复调参。

最佳轮次指标与 `best.pt` 不自动建立对应关系。归档时在 note 中写明评估命令、所用权重哈希与结果来源；无法证实时标注不确定，不能将它当作经核验的最优权重。

## 修订、冲突与调用

记录不可通过 CLI 原位编辑；supersedes 链保留历史，同一旧版本只能有一个后继。附件属于具体版本，修订不会自动继承附件，防止新指标错误引用旧权重。需要沿用附件时重新确认对应关系后 attach。

supports/contradicts/evaluates/follows_up 关系保存显式说明，禁止跨项目自动关联。程序不自动判断矛盾；助手或研究者需根据证据添加关系。brief 的调用记录证明哪些版本被返回，不证明用户已经采纳。

## 备份与边界

数据库使用 SQLite 事务；附件按 SHA-256 保存并去重，源文件修改不会覆盖已归档内容。备份包含数据库和所引用附件，并执行完整性检查。备份不是加密，也不是外部防篡改账本；拥有文件写权限的人仍可修改数据库。需要跨设备共享时，由用户选择受控存储和访问方式。

检索是中文子串/空格分词匹配与结构化过滤，不是语义向量检索。数据库适合个人/课题组的小规模本地记录，未提供多租户鉴权、自动云同步或大规模检索性能保证。长期使用应定期备份并审查失效建议。
