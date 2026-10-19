# 审稿意见对照核查与修订计划

> 审查对象：审稿意见《Engineering Trade-offs in Merkle-Aggregated Winternitz Signatures》（建议：大修）
> 对照稿：`paper/paper_jce.md`（当前工作树版本，2026-10-19）
> 核查方式：通读论文全文，并与工件逐一核对——`experiments/results_submission.json`、`experiments/sphincs_benchmark.json`、`audit/audit_jce.json`、`audit/state_model_jce.json`、`experiments/kat_128s.rsp`，以及确定性重跑 `audit/state_model_jce.py`。

---

## 0. 总体判断

审稿人要求大修，核心缺口归为三类：①密码学安全证据边界；②工件外部化（公开仓库 / DOI / 固定版本）；③实验强度与计数口径。对照当前稿：

- **审稿要求的"表述与边界"类修改，当前稿绝大部分已经完成**：路线 A 定位、术语区分（Winternitz prototype vs WOTS+）、标准方案比较免责声明、状态模型抽象定位、Bitcoin 集成边界、附录向量标注。
- **仍存在的实质缺口集中在**：工件公开（作者操作）、独立测试向量（本稿无法完成，须继续列为局限）、修复版实验覆盖（缺签名 / 密钥生成计时与分布呈现）、以及一处数字错误（§7.5 状态模型）。

**本核查新发现（投稿前必须修正）**：论文 §7.5 写 "reaches **52** distinct states and checks **351** transition occurrences"，但确定性重跑 `audit/state_model_jce.py` 与 `audit/state_model_jce.json` 均为 **73 个状态 / 355 次转移**。这是审稿人 4.1 所要求"计数口径统一"的一个直接反例，须在投稿前修正（行动 A）。

---

## 1. 六项主要问题逐条核查

### 问题 1：修复校验和不等于证明密码学安全（§4、7）— 部分满足

**审稿要求**：补充独立测试向量、正确性测试、明确安全目标；将"实现通过测试"与"方案具有密码学安全性"分开陈述。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 分开陈述 | §4.2 "No unforgeability theorem or numerical forgery bound follows from these checks."；§7.1 "This revision provides no proof in either a classical or quantum random-oracle model" 且 "two implementations sharing the same mistake may agree perfectly"；摘要 "no cryptographic security level is assigned"；§2.2/§2.4 术语与定位 | ✅ 已满足 |
| 明确安全目标 | §7.1 隐含（无安全等级主张），但未用一句话显式化 | ⚠️ 建议补一句（行动 F） |
| 独立测试向量 | Appendix A 本地回归向量明确标注 "not a NIST conformance vector"；无第三方独立向量——现实局限 | ⚠️ 保持如实披露即可，不建议伪造 |

**结论**：审稿人最核心的要求（分开陈述）已达成；行动 F 是低成本强化。

### 问题 2：实验可复跑但独立复现条件不完整（§3、6、9）— 部分满足

**审稿要求**：投稿前公开源代码、原始 JSON、生成脚本、依赖版本、运行命令和校验值，固定版本；匿名评审可先匿名归档。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 运行命令 / 依赖 / 校验值 | §9.1 复现命令（任意目录可跑）；`results_submission.json` 含 environment、raw_samples×270、artifact_hashes（SHA-256 四脚本）；README 依赖表 | ✅ 论文层面已备 |
| 诚实披露缺失 | §9.2 "has not been assigned a public repository URL, release identifier, or archival DOI" 明确须投稿时补 | ✅ 已披露 |
| 公开仓库 / DOI / 固定版本 | 无——作者操作 | ❌ 缺口（行动 B，对应 SUBMISSION_CHECKLIST 待办 2） |
| 工件清单可核对 | `ARTIFACT_MANIFEST.txt` 文件名为扁平形式，与当前子目录结构不一致（README 已知事项 6） | ⚠️ 建议更新（行动 C） |

**结论**：论文层面披露与运行入口齐全；外部化动作须由作者完成。

### 问题 3：性能结果尚不足以支撑广泛的性能结论（§3、6）— 部分满足

**审稿要求**：区分单次签名/验证计时、整树密钥生成开销、树间差异、环境与测量顺序；同树多次观测 ≠ 独立实验；提供原始样本分布。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 历史实验局限披露 | §3.2 如实说明（10 次重复、固定消息/叶子、缓存）；§6.1 表 6 标注 legacy | ✅ |
| 独立树 vs 重复观测 | §6.4 "three independently generated trees … 15 measured leaves per tree"；"shared trees and a single host preclude interpreting the observations as independent deployment trials"（JSON 已核实每配置 3 树） | ✅ |
| 不声称显著性 | §6.6 "no significance test or confidence interval is claimed"；原始样本（raw_samples×270）保留 | ✅ |
| 修复版单次签名计时、整树密钥生成计时 | 表 8 只有验证计时；修复版无签名 / 密钥生成列 | ❌ 缺口（可选：行动 H） |
| 树间差异 / 样本分布呈现 | raw_samples 含 tree 字段与原始计时，论文未做 tree-level 汇总或分布呈现 | ⚠️ 可选补强（行动 H） |
| "540 次验证计时观测"口径 | 未显式写明 | ⚠️ 行动 D |

**结论**：边界与披露到位；补强方向是实验覆盖与数据呈现，非改写定位。

### 问题 4：与标准方案比较必须严格限制解释范围（§2、6）— 已满足

**审稿要求**：标注"尺寸背景参考"，不作同条件性能排名；若主张性能优势须同平台、同操作边界、合理匹配标准实现。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 尺寸背景标注 | 表 7 题注 "Size context only; these rows do not represent equivalent security guarantees, key lifetimes, or serialization conventions."；§6.3 "It is not evidence that the implemented scheme delivers an equally secure signature at half the size." | ✅ |
| 不主张超越 | §2.4 "The study does not demonstrate that the proposed implementation outperforms standardized XMSS, LMS, or SLH-DSA." | ✅ |
| 同机基准 | §6.7 表 10：同机 SLH-DSA-128s/128f C `-O3` 基准（已核实 `sphincs_benchmark.json`：n=100、均值/中位数/SD 齐全），题注 + 正文双重声明 "context baseline, not a like-for-like speed comparison" | ✅ |

**结论**：完全满足；回复信直接引用表 7 / §6.3 / §6.7 即可。

### 问题 5：状态模型安全性质尚未在真实持久化系统中验证（§7、8）— 部分满足

**审稿要求**：增加持久化状态测试、崩溃注入和并发测试；明确哪些状态更新必须在签名离开设备之前完成；若无实际实现，应作为形式化或抽象模型结果报告。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 抽象模型定位 | §7.4 表 11：S2/S3 明确 "Assumed, not implemented"；§7.5 "neither tests a storage engine nor emulates concurrent processes or Byzantine hardware" | ✅（审稿人接受的报告方式已做到） |
| 状态机可复现 | `state_model_jce.py` 确定性重跑通过（**73 状态 / 355 转移**，见新发现） | ✅（但论文数字写错，行动 A） |
| 签名离开设备前的时序要求 | §7.2 提及 "atomic leaf reservation before a signature can leave the device"，但未显式总结为一条时序约束 | ⚠️ 行动 G |
| 真实持久化 / 崩溃注入 / 并发测试 | 未做；§9.3 第 3 条已如实列为更强评估要求 | ❌ 现实局限，保持披露 |

**结论**：定位正确、边界诚实；真实验证属实现工程，不建议在本稿硬补。

### 问题 6：创新性与文献定位（§1、2、8）— 基本满足

**审稿要求**：说明相较于既有实现审计 / 载荷分析 / 状态管理研究的具体新增；三个贡献分别给出证据；文献逐条核对。

| 审稿要求 | 当前稿证据 | 判定 |
|---|---|---|
| 贡献边界 | §1 "claims neither a new signature primitive nor priority for those techniques"；C1/C2/C3 明确 | ✅ |
| 与既有研究定位 | §2.4 分别对标 McGrew 状态管理、Hülsing W-OTS+、Romansky 基准 | ✅ |
| 三贡献证据 | C1→§4.2/§5（audit 可复现）；C2→§6.4/§6.5（JSON 可复现）；C3→§7.4（反例可复现） | ✅ |
| 文献逐条核对 | BIP 360 v0.12.1（2026-09-28 访问）与 FIPS 204/205 已核验（SUBMISSION_CHECKLIST 记录）；其余 8 条待人工复核 | ⚠️ 行动 I（P2） |

**结论**：主体定位满足；剩余为文献收尾动作。

---

## 2. 技术核查逐条

### 4.1 实验样本数表述 — 部分满足

- **已核验一致**：`results_submission.json` total_signing_events=270、total_counted_checks=5130、checks_per_event=19、raw_samples=270；论文 §6.4/§6.5/§10 与之一致。
- **缺口**：论文未显式给出①独立树总数（18 = 3×6 配置）、②验证计时观测总数（540 = 2 模式 × 270 事件）、③功能检查分解（540 正 + 4,320 负 + 270 重复索引拒绝）。
- **行动**：D（§6.4 加一句口径总结）。

### 4.2 载荷模型与序列化格式对应 — 部分满足

- 论文现有：表 3（组件计数：w=256,h=4 → 2,304 / 1,216 B）、§6.4 编码说明（8 字节头部）、表 8（含头字节：2,312 / 1,224 B）。
- **缺口**：没有一张字段级拆分表。审稿人示例已复核：**1,088（34×32 链元素）+ 128（4×32 路径）+ 8（头部）= 1,224 B** ✓。
- **行动**：E（§6.4 或附录加字段级拆分表，至少给出 w=256,h=4 一例）。

### 4.3 链计算理论期望与计时结果区分 — 已满足（可选增强）

- 分层清楚：§5.2/§5.3 理论（表 4 实际计数 + 表 5 精确期望，`audit_jce.json` 可复现）；§6.1 legacy 计时；§6.4 修复版验证计时；§6.2 C 微基准边界。
- 论文未把链调用减少解释为整体延迟同比下降（§6.4 "no uniform latency advantage is expected or claimed"）✓。
- **可选增强**：修复版 chain-call 实际计数（确定性）可补为表 4b（行动 J，P2）。

### 4.4 Bitcoin 集成定位 — 已满足

- 章节定位为 "Bitcoin-Oriented Integration Model"；§8.2 明确无交易序列化 / 共识 / 验证、`bc1z` 非 Bech32m、3 字节脚本为占位；§8.3 修正 4,461 字节核算并声明非完整费用估算。
- **行动**：无需改动。

### 4.5 参考文献与附录 — 已满足（附录）/ 部分满足（文献复核）

- **已核验**：`kat_128s.rsp` 内容确为 "404: Not Found"（14 字节），且未被任何活动代码（audit/experiments/src）引用，不会混入验证通过集合 ✓；Appendix A 明确标注本地回归向量非 NIST 一致性向量 ✓。
- 文献：BIP 360 v0.12.1、FIPS 204/205 已核验；其余建议人工逐条复核（行动 I，P2）。

---

## 3. 审稿"修改顺序"清单映射

| 审稿清单项 | 当前稿状态 | 证据 | 主要动作 |
|---|---|---|---|
| 1. 明确论文定位与核心主张 | ✅ 已满足 | Abstract、§2.2、§2.4、§7.1、§9.3 | 无 |
| 2. 开放实验工件并核对所有数字 | ⚠️ 部分满足 | §9.1/§9.2；但 §7.5 数字错误；MANIFEST 路径过时 | A、B、C |
| 3. 补强独立验证与状态测试 | ⚠️ 部分满足 | §7.5 可复现；独立向量 / 持久化测试列局限 | F、G（A） |
| 4. 收紧标准方案比较 | ✅ 已满足 | 表 7、§6.3、§6.7 | 无 |
| 5. 整理图表、文献和行文 | ⚠️ 部分满足 | §7.5 数字、字段表、文献复核、计数口径 | A、E、D、I |

---

## 4. 优先修订行动计划

### P0 投稿前必须

| # | 动作 | 类型 | 对应审稿点 |
|---|---|---|---|
| A | 修正 §7.5：52/351 → **73/355**（与 `state_model_jce.json` 及重跑结果一致） | 自动可做 | 问题 5、4.1 |
| B | 公开仓库 + Zenodo DOI + tag v1.0，回填 §9.2 与 `CITATION.cff` | 作者操作 | 问题 2 |
| C | 更新 `ARTIFACT_MANIFEST.txt` 为当前子目录路径（README 已知事项 6） | 自动可做 | 问题 2 |

### P1 下一轮修改

| # | 动作 | 类型 | 对应审稿点 |
|---|---|---|---|
| D | §6.4 补计数口径：18 棵独立树 / 270 签名事件 / 540 验证计时观测（每模式 270）/ 5,130 检查（540 正 + 4,320 负 + 270 重复索引拒绝） | 自动可做 | 4.1 |
| E | 加字段级序列化拆分表（w=256,h=4：1,088+128+8=1,224 B） | 自动可做 | 4.2 |
| F | §7.1 末加显式安全目标声明（本稿不主张任何安全等级 / EUF-CMA 目标） | 自动可做 | 问题 1 |
| G | §7.2/§7.4 显式总结"签名离开设备前必须完成原子预留"的时序约束（S2 与 Emit 之间） | 自动可做 | 问题 5 |
| H | 可选：从 raw_samples 补 tree-level 均值/分位数；如需补修复版签名 / 密钥生成计时则重跑实验（数字会变，需作者确认后再改正文） | 自动/作者 | 问题 3 |

### P2 收尾 / 可选

| # | 动作 | 类型 | 对应审稿点 |
|---|---|---|---|
| I | 文献逐条核对清单（10 条引用的版本 / 作者 / 出版信息 / 正文引用关系） | 作者 | 问题 6、4.5 |
| J | 可选：修复版 chain-call 计数表（表 4b，确定性） | 自动可做 | 4.3 |
| K | 起草审稿回复信时引用已满足项证据（§4.2/§7.1、表 7、§6.3、§6.7、§8.2、Appendix A） | 自动可做 | 全部 |

---

## 5. 证据核对记录（本次核查）

| 数据项 | 论文位置 | 工件来源 | 核对结果 |
|---|---|---|---|
| 270 个签名事件 | §6.4、§10 | `results_submission.json` total_signing_events / raw_samples | ✅ 一致 |
| 5,130 次功能检查（19/事件） | §6.5、§10 | `results_submission.json` total_counted_checks / checks_per_event | ✅ 一致 |
| 表 2 校验和缺陷（178 / 451 / 3,706） | §4.2 | `audit_jce.json` table2_checksum_defect | ✅ 一致 |
| 表 4 链调用（206/193/399 等） | §5.2 | `audit_jce.json` table4_exact_chain_work | ✅ 一致 |
| 表 3 载荷（8,640/4,384 等） | §5.1 | `audit_jce.json` byte_accounting | ✅ 一致 |
| 1,224 B 字段拆分（1,088+128+8） | §6.4 | 复算：34×32 + 4×32 + 8 | ✅ 一致 |
| 表 10 SLH-DSA 128s/128f | §6.7 | `sphincs_benchmark.json`（n=100，均值/中位数/SD） | ✅ 一致 |
| kat_128s.rsp = "404: Not Found" | Appendix A | 文件内容 14 字节；未被任何活动代码引用 | ✅ 一致 |
| §7.5 状态模型规模 52/351 | §7.5 | 重跑 `state_model_jce.py` = **73/355** | ❌ **不一致，须修正** |
| 表 8 验证计时（0.932 等） | §6.4 表 8 | `results_submission.json` configs（0.266 等） | ❌ **不一致，须修正** |
| §6.4 运行环境（CPython 3.7.3 / x86_64） | §6.4 | JSON environment（CPython 3.14.7 / arm64） | ❌ **不一致，须修正** |
| 表 9 路径消融（0.0405 等） | §6.5 表 9 | `figures/path_traversal.json`（0.0065 等） | ❌ **不一致，须修正** |

---

## 6. 本轮执行结果（2026-10-19）

### 6.1 执行中发现并已修复的追加问题（审稿人问题 2 的核心关切）

对照保留工件逐表核对时发现：**论文表 8（修复版验证计时）、表 9（路径消融）、§6.4 运行环境描述均与保留工件不一致**。论文旧值（如 w=256,h=4 验证 7.657 ms、CPython 3.7.3 / Darwin 24.6.0 / x86_64）来自一次未归档的运行；保留工件 `results_submission.json`（CPython 3.14.7 / macOS 15.7.7 / arm64）自首个提交起即为当前数值（w=256,h=4 实测 2.259 ms）。这也导致旧 HTML 内嵌的 Figure 3（9 月 28 日版本）与表 8 相互矛盾。

**修复方式**：以保留工件为权威来源——表 8 按 `results_submission.json` 的 configs 汇总（均值 ± 样本标准差）更新；表 9 按重新生成并经 figure 脚本同步的 `figures/path_traversal.json` 更新（figure3.png/svg 与 fig_submission.png 同步、哈希一致）；§6.4 运行环境改为 CPython 3.14.7 / macOS 15.7.7 / arm64（与 §6.7 表 10 环境一致）；HTML 经 `render_jce.py --from-markdown` 重渲染（12 张表、图 3 为新版 base64 内嵌）。所有结论方向不变（w=256 验证最慢、重建路径远慢于缓存、1,224 B 最小载荷等）。

### 6.2 计划项执行状态

| 计划项 | 状态 | 说明 |
|---|---|---|
| P0-A 修正 §7.5（52/351 → 73/355） | ✅ 完成 | 与 `state_model_jce.json` 及重跑一致 |
| P0-B 公开仓库 + Zenodo DOI + tag v1.0 | ⏳ 作者操作 | 无法代为完成；投稿前必须（对应 SUBMISSION_CHECKLIST 待办 2） |
| P0-C 更新 ARTIFACT_MANIFEST.txt | ✅ 完成 | 改为仓库根相对路径、重算 SHA-256、新增 paper_jce.md（20 项） |
| P1-D §6.4 计数口径 | ✅ 完成 | 新增"18 棵独立树 / 270 事件 / 540 验证观测（270/模式）" |
| P1-E 字段级拆分表（表 8a） | ✅ 完成 | 6 配置 ×（链元素/路径/头部/合计），与表 8 字节列一致 |
| P1-F §7.1 安全目标声明 | ✅ 完成 | 明确不主张任何安全性质 |
| P1-G §7.4 durable-before-release 约束 | ✅ 完成 | 显式化 Reserve 先于 Emit 的时序约束 |
| P1-H tree-level 汇总/签名计时 | ⏸️ 保留可选 | 原始样本含 tree/index，JSON 可复算；补签名计时需重跑实验（数字会变，需作者确认） |
| P2-I 文献逐条核对 | ⏳ 待作者 | BIP 360、FIPS 204/205 已核验；其余 8 条建议复核 |
| P2-J 修复版 chain-call 计数表 | ⏸️ 保留可选 | 确定性可算，未纳入本轮 |
| P2-K 审稿回复信 | ✅ 完成 | `reports/RESPONSE_TO_REVIEWERS.md` |

### 6.3 追加核查记录（本轮）

| 数据项 | 论文位置 | 工件来源 | 核对结果 |
|---|---|---|---|
| 表 8 新值（0.266±0.202 等 6 行） | §6.4 表 8 | `results_submission.json` configs | ✅ 一致（逐行复算） |
| 表 8a 字段拆分（4,392…1,224） | §6.4 表 8a | 复算 L×32 + h×32 + 8 = 表 8 字节列 | ✅ 一致（6 行） |
| 表 9 新值（0.00646…0.09992） | §6.5 表 9 | 重新生成后的 `figures/path_traversal.json` | ✅ 一致（6 行） |
| Figure 3（figure3.png == fig_submission.png） | §6.4 图 3 | 本次 `make_submission_figure.py` 重生成 | ✅ 哈希一致（1cded96d…） |
| HTML 重渲染 | paper_jce.html | `render_jce.py --from-markdown` | ✅ 旧值清零、新值齐全、12 表、图 3 内嵌 |
| 5,130 检查分解 | §6.5 | 脚本 19/事件；270 记录中 180 次真实重复索引拒绝 | ✅ 已精确化表述 |

---

## 7. 第二轮审稿对照与执行记录（2026-10-19）

第二轮意见确认第一轮修订方向正确（定位诚实、接口完整、局限披露充分），核心要求收敛为三点：①5,130 检查口径可自动复现；②高方差计时补稳健统计并弱化速度比较；③继续严格区分功能正确性/标准符合性/密码学安全。以下逐条映射本轮执行。

### 7.1 核心问题 1 — 检查统计口径（已解决，脚本自动复现）

审稿人要求解释"每树 15 叶"与"180 条真实重复"的关系，并在附录给出由脚本自动生成的计数表。

- **机制说明（已写入 §6.5）**：进程内 used-index 集合**按 (w,h) 配置新建、在该配置的 3 棵树间累积**，15 个测量索引在树 0 首次使用、在树 1/2 为真实重复；不同配置不共享集合。故 270 条重复索引记录中 180 条真实拒绝、90 条首次使用。
- **自动复现（新增）**：`experiments/check_counts.py` 从 `results_submission.json` 确定性汇总每类检查的执行次数/预期/实际，断言全部通过，输出 `experiments/check_counts.json`；论文**附录 B 表 13** 即其渲染。每配置 45 事件 = 90 正向 + 720 拒绝 + 45 重复索引记录（30 拒/15 首用）。
- **计数验证**：270×19=5,130；正向 540、拒绝 4,320、重复索引记录 270（拒 180/首用 90），脚本输出与 JSON 逐值一致。

### 7.2 核心问题 2 — 高方差计时（已解决：稳健统计 + 弱化结论）

- **新增表 8b**（§6.4）：6 配置 × 显式/紧凑中位数与 IQR、配对差值 Δ 中位数、显式更慢占比；由 `experiments/robust_stats.py` 从原始样本生成，**全部样本保留、未删除任何异常点**。
- **正文弱化**：明确"尺寸节省是主要可测结果；时间差异为探索性观察；不主张均匀延迟优势"。对 w=256,h=8 紧凑模式（均值 2.461 ± SD 6.077 ms，中位数 1.5315 ms，单样本最大 42.253 ms）给出长尾解释，而不是删除样本。
- **配对差值分布**：Δ 中位数 ≤0.02 ms，显式更慢占比 58–87% —— 两个编码在延迟上无系统差异。

### 7.3 核心问题 3 — 证据分层与措辞（已解决）

- **§2.2 新增三层证据框架**：算术审计（确定性推导）/功能测试（采样输入）/密码学分析（本文明确缺席）；功能正确不蕴含标准符合性，两者都不蕴含安全性。
- **全文措辞审计**：grep 全文确认统一使用 repaired variant / repaired research variant / fixed-prefix construction，无 "repaired WOTS+" 或标准符合性误导表述。

### 7.4 核心问题 4 — SLH-DSA 基准（已强化定位）

- 表 7 题注补充目的句："尺寸比较与参考计时，非 Pareto 优势或安全等价证据"；§6.7 保留原有差异说明（C 参考实现 vs CPython 原型、安全等级未指定）。

### 7.5 核心问题 5 — 状态恢复前提（已补充故障场景表）

- **新增表 12**（§7.4）：5 类故障场景（签名后崩溃/提交后未发送/恢复旧备份/并发抢索引/未确认广播后重组）逐条给出模型处理、是否保持不复用、代价（烧叶/浪费叶/停用根/需并发协调）。
- 明确该表是对模型假设的分析，不是对任何钱包实现的验证（遗留工件无持久化与多进程协调）。

### 7.6 细节修改

- §5.1 公式旁注明：指定实验编码的字节数，非网络协议或 Bitcoin witness 完整大小。
- §6.5 消融表述：特定实现消融，非生产级 Merkle 遍历通用结论。
- §8.1 首句：Bitcoin-oriented illustrative accounting，非协议集成。
- §9.1 复现命令新增 `check_counts.py` 与 `robust_stats.py`（确定性、无需重跑计时）。
- 文献 **[7]** 补访问日期（2026-10-19，PDF 可访问、版本 2026-09-24 与引用一致）；**[10]** 补 master 提交哈希 `e7263a4cfe50`（2026-08-03，GitHub API 核验），正文 §8.1 同步。

### 7.7 本轮证据核对

| 核查项 | 位置 | 权威来源 | 结果 |
|---|---|---|---|
| 表 8b 稳健统计（6 行） | §6.4 表 8b | `experiments/robust_stats.json` | ✅ 逐值一致 |
| 表 13 检查计数（6 行） | 附录 B 表 13 | `experiments/check_counts.json` | ✅ 逐值一致（270/270/4,320/90/180/5,130） |
| 表 8/8a/9/10/2/3/4/5/6、§7.5、270/5,130 | 原 11 项 | 各保留 JSON | ✅ 无回归（重跑全过） |
| HTML 重渲染 | paper_jce.html | `render_jce.py --from-markdown` | ✅ 380,979 B、13 节、15 表、图 3 内嵌、校验通过 |
| ARTIFACT_MANIFEST.txt | 仓库根 | 重算 SHA-256 | ✅ 25 项（新增 check_counts/robust_stats 脚本与 JSON、render_jce.py） |
| 文献 [7][10] | 参考文献 | 在线核验 | ✅ 均可访问；[10] 已钉提交哈希 |

### 7.8 仍待作者操作（未变）

公开仓库 + Zenodo DOI + tag v1.0 回填 §9.2；正式投稿译英与 Springer 模板转换；可选补修复版签名/密钥生成计时（会改表 8 数值）。

---

## 8. 第三轮审稿对照与执行记录（2026-10-19）

第三轮审稿确认前两轮方向，提出新的 **P0 级真实缺陷**：一次性密钥身份混淆。以下逐条记录。

### 8.1 P0 — 密钥身份混淆（已修复并重跑）

**问题确认**：`experiment_submission.py` 原 used-index 集合按叶子索引跨 3 棵树累积（`used_ok = leaf in used_indexes`），把不同密钥树中相同索引误判为同一一次性密钥的重复使用。而 `leaf_seed` 绑定 tree seed，各树密钥材料独立，K_{A,5} ≠ K_{B,5}。审稿判断成立。

**修复**：
- 实验代码改为 `used_keys` 按 **(tree, index)** 键（`kid = (t, leaf)`）；聚合字段 `key_identity`（first_use_events=45、rejected_reuse_attempts=0/配置）。
- **重跑实验**（`experiment_submission.py`，6.5 秒）：270 事件全部为不同 (tree, index) 密钥的首次使用，0 次误判；计时数值为本机新运行值（表 9/9b/图 3 全部更新）。
- **审计新增 key-identity 状态测试**（`audit_jce.py`，确定性、无计时）：同树同索引首次→允许、重复→拒绝；同树异索引→允许；异树同索引→允许；崩溃重启后重放已消费索引→拒绝。5 项全部符合预期（`all_as_expected=true`）。

### 8.2 P0 — 检查次数 vs 独立测试覆盖度（已解决）

- §6.5 与附录 B 明确：**5,130 是执行断言数（19×270），不是独立测试案例数**。
- 独立案例口径（附录 B 新增）：270 个互不相同的 (w,h,tree,index,message) 签名事件（跨 18 棵树）+ 16 种拒绝检查类型（8 类×2 模式）+ 审计确定性检查（5 项密钥身份场景、每 w 的修复版往返/篡改/错误消息/截断、表 5–6 的字节/链调用/校验和核算）。
- 随机篡改被拒绝 ≠ 不可伪造性：原有限定保留并在 §4/§6.5 再次声明。

### 8.3 P1 — 统计独立性（已补强）

- **树级分组**：§6.4 新增 Tree-level grouping 段，3 棵树为分组单位，15 叶共享根与路径结构非独立重复；示例 w=256,h=8 显式中位数跨树 1.455–1.628 ms；`robust_stats.py` 输出每树中位数（`tree_level`）。
- 配对差值、中位数/IQR 已在表 9b；"无显著性检验、无置信区间"的声明保留（§6.6）。
- 270 事件 vs 18 树的分开报告已保留；固定/随机化顺序、预热边界沿用 §6.4/6.6 原文，独立批次/多机复测列入 §9.3。

### 8.4 P1 — checksum 修复测试（已补强）

- §4.2 新增 "Repaired-encoding consistency"：每 w 的 消息数字/校验和数字/链调用总数/序列化长度一致性由 `audit_jce.py` 确定性检查（T_sign+T_verify = L(w−1)、L = L₁+L₂，表 5–6/9）。
- 明确无外部独立测试向量；本地回归向量（附录 A）自生成、非标准符合性向量；修 checksum 不改变 fixed-prefix 链函数的标准符合性状态。

### 8.5 公式/数据/章节核查落实

| 审稿点 | 落实 |
|---|---|
| 4.1 载荷公式复核（8,640/4,384/4,392 等） | ✅ 数字一致（表 4）；"非完整网络/交易开销"限定保持；§5.1 新增参数/索引/签名/根由谁提供及验证者信任来源句 |
| 4.1 载荷节省与完整验证同图 | ✅ 表 9 同时含字节与完整验证计时；正文重申无均匀延迟优势 |
| 4.2 链调用核对（206+193=399 等） | ✅ 表 5 数字复核一致；§5.2 加可独立验证说明（audit_jce.json） |
| 4.3 旧/修复/标准三标记 | ✅ §2.2 新增三标签定义（Legacy prototype / Repaired experimental variant / Standardized reference），全文统一 |
| §1–2 相关工作差异表 | ✅ 新增 **表 1**（对象/原始样本/完整验证/持久化状态/标准符合实现），表号全局重排 1→2 … 13→14、8a/8b→9a/9b |
| §6 重实验同步 | ✅ 重跑计时 + 表 9/9b/图 3/表 14/§6.5 全部同步新数值 |
| §7 三层证据 | ✅ §2.2 三层框架 + §7.5 状态测试指针；不把有限状态探索表述为生产防重用 |
| §8 收敛 | ✅ §8.3 明确假设逐项列出（witness 项数、长度前缀、脚本占位、bc1z 非 Bech32m、直接 MSS 承诺） |
| 文献 | ✅ [7][10] 已钉版本/访问日期/提交哈希（第二轮）；[9] 仅作动机基准（§2.4 表 1） |

### 8.6 本轮证据核对

| 核查项 | 结果 |
|---|---|
| 表 3–7/9/9a/9b/10/11、§7.5（73/355）、270/5,130 | ✅ 全部与工件 JSON 逐值一致（新运行数据） |
| 表 14 检查计数（270 首用 / 0 拒绝 / 5,130） | ✅ 与 check_counts.json 一致 |
| 审计密钥身份状态测试（5 场景） | ✅ all_as_expected=true |
| results_submission key_identity（0 误判） | ✅ 6 配置全部 0 |
| 表号重排完整性 | ✅ 1–14 + 9a/9b 齐全、引用同步 |
| HTML 重渲染 | ✅ 390,373 B、13 节、16 表、校验通过 |
| 图 3 同步 | ✅ figure3.png == fig_submission.png（0c11a942…） |
| MANIFEST | ✅ 25 项重算 SHA-256 |

### 8.7 仍待作者操作（未变）

公开仓库 + Zenodo DOI + tag v1.0 回填 §9.2；正式投稿译英与 Springer 模板；可选补修复版签名/密钥生成计时之外的独立批次/多机复测。

---

## 9. 第四轮审稿对照与执行记录（2026-10-19）

第四轮审稿与前几轮方向一致，为确认性 + 收尾性意见，未发现新的实现级缺陷。核心可执行项与落实如下。

### 9.1 P0-1 安全边界贯穿全文（已强化）

| 审稿要求 | 落实 |
|---|---|
| "repaired" 定义为编码缺陷修复而非安全修复 | §2.2 新增显式句：`"repaired" refers strictly to the identified encoding defects—checksum digit extraction and serialization accounting—and not to a repaired cryptographic-security property` |
| 单独列出攻击面/未证明性质/适用边界 | §7.1 新增 "Attack surface, unproven properties, and applicability boundary" 五条清单（不可伪造性、域分离、侧信道与故障、状态持久性、适用边界） |
| 不给出安全位数/抗伪造等级/安全等价 | 全文已遵守（摘要、§7.1 Security goal、表 8、结论）；本轮无新增越界表述 |
| 独立测试向量 | 如实声明不存在（§4.2/附录 A）；自生成回归向量标注为本地回归用途 |

### 9.2 P0-2 复算 270/540/5,130（已复核）

- 270 签名事件 × 2 模式 = 540 验证计时：§6.4 新增"四种统计单位"显式清单（270 事件 / 540 计时 / 18 棵独立树 / 270 个新消息摘要，分别报告、不可互换）。
- 5,130 = 19 × 270 断言数，独立案例口径已在第 3 轮（附录 B）。
- 第 3 轮 12 项回归检查本轮全部重跑通过；表 3–11/9a/9b/14 与工件 JSON 逐值一致。

### 9.3 P0-3 状态恢复论证（新增模型级确定性测试）

- §7.4 新增 "Three evidentiary levels" 段：抽象模型性质（S1–S5 条件不变量、命题 1/2）/ 实现性质（审计测试、进程内 (tree,index) 账本）/ 系统性质（未验证：无真实存储引擎、多进程、钱包集成）。明确"披露局限不消除其影响；论文主张限定在前两层"。
- **audit_jce.py 新增 `state_boundary_tests()`**（确定性、无计时）：①并发分配交错模拟（3 个固定种子 × 12 请求，线性化分配器语义下无重复分配、全部释放）；②快照恢复（B 单调、已消费索引保持消费）；③旧备份回滚（B 减少被 Recover 检测 → 停用根，不重发已消费索引）。3 场景全部 `all_as_expected=true`。
- 边界如实标注：非存储引擎、非真实线程、非多进程；生产级并发/持久化仍属 §9.3 未验证项。

### 9.4 P1 对比口径与复现材料

| 审稿要求 | 落实 |
|---|---|
| 表 8 明确"非等安全等级比较" | 题注加粗标注；正文区分签名载荷/完整序列化/公钥/状态存储四类数量不可互换 |
| 旧/新实验分组不合并为提升百分比 | 已有（§6.2/§6.4 Runtime 段）；§6.4 四统计单位句强化 |
| 配对差值/比值 + 置信区间 | 表 9b 配对差值已有；无显著性检验、无置信区间的声明在 §6.6 保留 |
| 复现材料 | §9.1 命令、§9.2 工件与披露已有；审计描述同步更新 state-boundary tests |

### 9.5 P2 收尾

| 位置 | 落实 |
|---|---|
| §2 定位 | §2.4 末段加直接句："engineering evaluation of a small fixed-prefix artifact, not a design of a new cryptographic primitive" |
| §5 尺寸口径 | 表 4 题注加统一注记："Every size table in this paper (Tables 4, 9, and 9a) counts the specified experimental encodings and states which fields are included" |
| §8 集成边界 | §8.1 加成分归属句（脚本/地址编码属 BIP 360 提案、bc1z 与脚本占位为作者设想、MSS 直接承诺为简化模型）；§8.2 加根承诺绑定（算法/参数/密钥容量）与字段承载、验证成本边界 |
| 附录 A | 回归向量定位已有 |
| 参考文献 | [2][8][9] 补访问日期，统一 "accessed DD Month YYYY" 格式 |

### 9.6 本轮证据核对

| 核查项 | 结果 |
|---|---|
| 第 3 轮回归 12 项（表 3–11/9a/9b/14、73/355、270/5,130、图 3） | ✅ 全部 PASS |
| 第 4 轮新增 15 项（state-boundary 3 场景、攻击面、三层证据、表 8 标注、四统计单位、文献日期等） | ✅ 全部 PASS |
| HTML 重渲染 | ✅ 395,478 B、13 节、16 表、校验通过 |
| MANIFEST | ✅ 25 项重算 |

### 9.7 仍待作者操作（未变）

公开仓库 + Zenodo DOI + tag v1.0 回填 §9.2；正式投稿译英与 Springer 模板；可选独立批次/多机复测、修复版签名与密钥生成计时；真实的持久化/并发/回滚系统级验证（§9.3 第 3 项）。

---

## 10. 第五轮审稿对照与执行记录（2026-10-19）

第五轮为确认性 + 收尾性意见，与第 2–4 轮高度收敛，无新实现缺陷。可执行增量全部落地。

### 10.1 新增"假设—实现—测试"对应表（表 12a）

审稿人要求逐项说明关键假设所需证据。新增表 12a（§7.4，表 12 后）：

| 假设 | 所需证据 | 本文状态 |
|---|---|---|
| S1 并发预留线性化 | 多进程并发测试或数据库事务证明 | 未提供；仅模型级交错（§7.5） |
| S2 释放前持久化预留 | 崩溃注入测试（提交-释放顺序） | 未提供；修复实验仅进程内 (tree,index) 账本；durable-before-release 为假设 |
| S3 恢复不回退 B | 旧备份/快照回滚/版本冲突测试 | 模型级确定性回滚检测（停用根）；无存储引擎 |
| S5 无密钥克隆 | 密钥复制/备份/多设备威胁模型 | 未提供；操作假设 |

### 10.2 命题 2 结论精确化（§7.4）

新增 "Precise statement" 段，按审稿人建议表述：仅凭密钥种子与当前确认链历史，无法在所有执行中精确重建历史暴露集合；安全恢复需额外可信持久化暴露状态，或在无法确认时停用签名根；并明确这不是笼统的"状态不可恢复"主张（额外可信持久化状态下的恢复不在排除之列）。

### 10.3 载荷减少比例派生列（表 4）

审稿人复算 49.3% / 48.6% / 47.2%，核对一致。表 4 新增 "Recovery reduction (derived)" 列，题注明确：仅在所定义编码内计算（1 − recovery/explicit），非协议级缩减或安全等价；端点恢复减少传输字节但增加验证端链计算，是否值得取决于参数/传输/验证成本。论文不使用"更高效"等概括表述。

### 10.4 表格"测量/派生/示意"标注（P2）

16 张表题注统一加来源标记：表 3/4/5/6/9a = [Derived]；表 7 = [Historical measured aggregates]（并补"原样本未保留，仅历史汇总"句）；表 8 = [Illustrative/Derived]；表 9/10/11 = [Measured]；表 9b = [Measured; derived statistics]；表 12 = [Model assumption]；表 12a = [Model/evidence mapping]；表 13 = [Model]；表 14 = [Derived from raw records]。

### 10.5 §8 标题统一 + 摘要精简（P2）

- §8 标题改为 "Bitcoin-Oriented **Illustrative** Integration Model"。
- 摘要技术清单适度合并（两处 payload 跨度与 1,224 字节合为一句，去掉 "We define both wire formats"），保留研究问题→可验证结果→边界结构。

### 10.6 渲染脚本修复

第 5 轮发现 `render_jce.py` 只替换 `<article>`、保留旧 `<nav>`（TOC）导致 §8 标题改动后旧锚点残留、校验失败。修复：from_markdown 模式同时更新 `<nav>`；重渲染 398,592 B，链接全解析、无重复 id。

### 10.7 本轮证据核对

| 核查项 | 结果 |
|---|---|
| 表号完整性（含表 12a） | ✅ 1–14 + 9a/9b + 12a |
| 表 4 派生列（49.3/48.6/47.2%） | ✅ 与字节数一致 |
| 表 12a / Precise statement / 各题注标记 / §8 标题 / 摘要 | ✅ 全部存在 |
| 第 3/4 轮回归（表 3/5/9/9b/10/14、73/355、270/5,130、状态测试、图 3、安全边界、四统计单位、文献日期） | ✅ 全部 PASS |
| HTML | ✅ 398,592 B、17 表、链接全解析 |
| MANIFEST | ✅ 25 项重算 |

### 10.8 仍待作者操作（未变）

公开仓库 + Zenodo DOI + tag v1.0 回填 §9.2；正式投稿译英与 Springer 模板；可选独立批次/多机复测、修复版签名与密钥生成计时；真实的持久化/并发/回滚系统级验证（§9.3 第 3 项、表 12a 各"未提供"行）。

---

## 11. 第 6 轮补强（2026-10-19）：表 12a 的 SQLite 事务后端

审稿人要求把表 12a 中"未提供"的证据升级为真实系统级验证，并在"多进程并发测试**或**数据库事务证明"两条路线中任选其一。本轮在已有文件锁 allocator（§7.6 前半，`state_demo/`，6/6 测试）之外，新增独立的 **SQLite 事务后端**（数据库事务证明路线）：

- **实现**：`src/ledger_store.py`（纯标准库 sqlite3）。每次预留为 `BEGIN IMMEDIATE` 事务 + `UNIQUE (tree_id, leaf_index)` 主键；ledger epoch 在同一事务内单调递增并持久化；外部 checkpoint 文件保存最近成功运行的 epoch 供回滚检测。
- **测试**：`audit/state_persistence_tests.py`，三类确定性断言组，输出 `audit/state_persistence_tests.json`（`all_as_expected = True`）：
  1. **并发事务（S1）**：8 个 worker 进程（96 请求）与 16 线程（192 请求）竞争同一库文件——成功预留全部唯一、无重复无丢失；
  2. **崩溃注入（S2）**：`os._exit` 级崩溃——COMMIT 前崩溃 → 事务回滚、key 可重新预留；COMMIT 后崩溃 → 预留持久、重用被拒；
  3. **回滚检测（S3）**：一致快照恢复（epoch 不低于外部 checkpoint）→ 继续、已消费索引仍拒绝；旧备份恢复（epoch 低于 checkpoint）→ 检测到回退、停用签名根、不重发任何已消费索引。
- **论文落点**：表 12a 的 S1/S2/S3 状态列更新；§7.6 新增 "Database-transaction route" 段；§7.1 State durability 条目、§7.4 三层证据段、§9.1 命令、§9.2 工件、§9.3 第 3 项、结论均同步。
- **边界（如实披露）**：SQLite 覆盖**进程崩溃**级安全（未提交事务回滚、已提交事务幸存）；断电级持久性、多主机协调、硬件故障不在范围（§9.3 与测试 note 均声明）。S5（无密钥克隆）仍为威胁模型陈述，无代码级预防（未提供）。
- **验证**：md↔HTML 同步校验通过；19 表不变（未新增表）；MANIFEST 41 → 44 项。

**第 6 轮遗留**：表 12a 的 S5 行保持"Not supplied（操作假设）"；断电/多机/硬件故障验证继续列为 §9.3 后续工作；公开仓库 + Zenodo DOI + tag v1.0 仍为作者操作。


---

## 12. 第 7 轮：审稿执行方案对照与执行记录（2026-10-19）

用户提供《论文修改与实验执行方案》（12 部分），主线：先对齐安全性边界/实验对象/统计单位/可复现材料四件事，再补实验，最后改摘要结论。执行顺序按该主线落地。

### 12.1 基线冻结与复现验证（方案步骤 1、3.1）

- `git tag review-baseline-r7`（HEAD `c54d85a6`）已建立；19 个关键文件 SHA-256 入账。
- 确定性脚本重跑全过，5 个 JSON 哈希与基线完全一致：`audit_jce.py` / `state_model_jce.py` / `state_persistence_tests.py` / `state_demo/test_state.py`（6/6）/ `check_counts.py` / `robust_stats.py`（audit/state_model/state_persistence/check_counts/robust_stats JSON 全部 SAME）。
- 计时实验 `experiment_submission.py` **未重跑**：重跑生成新随机样本会替换第 3 轮权威数据（表 9/9b/14/图 3 全链），列为决策项；复现基线以保留工件为权威，符合审稿人"文件存在则不重建"原则。

### 12.2 方案 ↔ 现状对照（12 部分）

| 方案部分 | 判定 | 说明 |
|---|---|---|
| 1 冻结版本/目录结构 | ✅ 已做 | tag + 哈希入账；目录结构已满足（paper/src/audit/experiments/charts/bench/state_demo），未强改 |
| 2.1 三个概念统一 | ✅ 已达标 | fixed-prefix 非 WOTS+、Merkle 聚合不解决状态、持久化状态仅条件性（§2.2/§7.1/§7.4） |
| 2.2 摘要改写 | ✅ 已达标 | 现有摘要即"工程评估+可复现结果+边界"，无安全等价暗示 |
| 2.3 贡献点收敛 | ✅ 已达标 | C1/C2/C3 工程贡献，"claims neither a new signature primitive" |
| 3.1 复现基线 | ✅ 本轮执行 | 见 12.1 |
| 3.2 基线验收表 | ✅ 已覆盖 | 表 3/5/6/9 与 audit JSON 逐项对应；错误路径/篡改/截断拒绝在 repaired_checks |
| 3.3 checksum 边界测试 | ✅ **本轮新增** | 双独立 oracle（divmod 整数路径 + 序列化位串路径）vs 生产移位编码，w∈{4,16,256} 各 9 case（全零/最小/低中高位单 bit/最大可表示/消息可达最大/进位邻接/随机消息），27/27 全对拍 + 数字范围 + 位数 + 总长度不变量；`checksum_boundary_tests` 入 audit_jce.json；§4.2 已同步 |
| 4.1 固定参数 | ✅ 已达标 | n=32、w∈{4,16,256}、h∈{4,8}、双编码配对（§6.4） |
| 4.2 独立树 20-30 棵 | ⚠️ **决策项** | 当前 3 棵×15 叶×6 配置；扩展到 20-30 棵需重跑全部计时并重生成表 9/9b/14/图 3（数小时），不擅自执行 |
| 4.3 配对计时协议 | ⚠️ 部分 | 已配对（同消息双编码、45/行、表 9b 中位数+IQR+Δ+占比）；预热/30 次/5 会话/CPU 负载记录为增强项 |
| 4.4 计时边界拆分 | ⚠️ **决策项** | verify_total 已从序列化输入起算；parse/recover/leaf_hash/path_verify 分项未测（路径消融表 10 只有 rebuilt/cached 整体） |
| 4.5 统计单位 | ✅ 已达标 | 四统计单位（270 事件/540 计时/18 树/270 新消息）、树级中位数（robust_stats tree_level）、无显著性检验声明；bootstrap 为决策项 |
| 5.1-5.2 状态模型 B/C/E + 阶段 | ✅ 已达标 | §7.4 生命周期 + §7.5 模型；§8.2 暴露 vs 确认区分 |
| 5.3 状态测试矩阵 | ✅ 大部分 | 文件后端 6 测试（§7.6 表 14）+ SQLite 后端三类（并发/崩溃/回滚，§7.6）；重复请求/链重组/状态文件损坏为模型级或决策项 |
| 5.4 F1-F7 故障点 | ⚠️ **决策项** | 现有崩溃注入覆盖 COMMIT 前后两点 + 表 14 六场景；F1-F7 七点细化（before/after reservation/signature/confirmation/reorg）可加 |
| 5.5 并发测试 | ✅ 已做 | 8 进程 + 16 线程 + 崩溃重启 + 旧快照覆盖（SQLite）；单机多进程，多主机为决策项 |
| 5.6 验收指标 | ✅ 已覆盖 | 重复索引=0、误释放=0、通过数/注入点/未覆盖威胁在 JSON 与 §7.6 |
| 6 C 比较规范化 | ✅ 已达标 | build.sh 记录 clang 17.0.0、PQClean commit（会话 JSON）、无 pinning、clean 实现非 AVX2、分开测 keygen/sign/verify、非安全等价标注（§6.7/6.8/表 11/11a） |
| 7.1-7.2 两层统计/配对差值 | ✅ 已达标 | 树级汇总 + 配对 Δ（表 9b）；bootstrap CI 为决策项 |
| 7.3 图 A/B/C | ⚠️ **决策项** | 现有图 3（size-vs-time 权衡）+ 图 4（C 比较）；树级配对差值散点、状态覆盖矩阵未画 |
| 8 Bitcoin 二选一 | ✅ 方案 A | §8 已是 "Illustrative Integration Model"，4,461 字节理论估算、bc1z 非 Bech32m、无共识验证声明（§8.1-8.3） |
| 9.1 发布包 11 项 | ⚠️ 部分 | 源码/脚本/原始数据/环境/模型/故障测试/README 已在仓库；公开仓库 URL、DOI、许可证、tag 回填为作者操作 |
| 9.2 make reproduce | ✅ **本轮新增** | Makefile：`make test`（确定性审计，数秒）/ `reproduce-quick` / `reproduce-full`（含计时重跑警告） |
| 9.3 配置外置 | ⚠️ 决策项 | 参数在脚本常量（CONFIGS/TREES_PER_CONFIG 等）；独立 YAML 配置 + 结果-配置哈希映射为工程化增强 |
| 10 逐章节清单 | ✅ 已覆盖 | 历轮已逐节落实（见 §1-11） |
| 11 两周计划 | — | 已按主线压缩执行可自动化部分；决策项等待批准 |
| 12 五条判定标准 | ✅ 达标 4/5 | 正确性（含本轮边界测试）、性能口径、状态安全、结论边界达标；可复现性"公开可访问"待作者操作 |

### 12.3 本轮执行记录

- **竞态修复（真实缺陷）**：`state_persistence_tests.py` 偶发失败根因 = SQLite 首次打开竞态（`PRAGMA journal_mode=WAL` 写入使空文件变非空，破坏"首次建表"判定 → `no such table`）。修复：first-open 判定移到 journal_mode 之前 + journal_mode 竞态容错（OperationalError 跳过）。修复后 5 次循环全过（all_as_expected=True），`make test` 全链路通过。
- **checksum 边界测试**：`audit_jce.py` 新增 `checksum_boundary_tests`（见 12.2 3.3），audit_jce.json 新哈希 `f3d1440e…`。
- **Makefile**：`make test` 6 步确定性审计 + 渲染校验；`reproduce-full` 含计时重跑（带警告）。
- **论文同步**：§4.2 边界测试句升级（双 oracle、27 case）；§9.1 补 make test 行。HTML 重渲染 559,147 B、19 表、13 节、链接校验通过。
- **MANIFEST**：45 项（+Makefile；5 项重算）。

### 12.4 待用户决策（未擅自执行）

1. **独立树扩展 4.2**：3 棵 → 20-30 棵（重跑计时，替换表 9/9b/14/图 3 权威数据；需确认预算与是否接受新样本）。
2. **计时分项 4.4**：parse/recover/leaf_hash/path_verify 分项计时。
3. **图 A/B/C 与树级 bootstrap 7.3**。
4. **F1-F7 故障点细化 5.4**。
5. **配置外置 9.3**（YAML + 结果-配置哈希）。
6. **`make reproduce-full` 执行**（含计时重跑）。

### 12.5 作者操作（未变）

公开仓库 + Zenodo DOI + tag v1.0 回填 §9.2；正式投稿译英与 Springer 模板；许可证文件。


---

## 13. 第 8 轮：BIP 360 数据集相关性核查（2026-10-19）

用户要求核查项目数据与 BIP 360（github.com/bitcoin/bips bip-0360.mediawiki）数据集的相关性，并保障数据权威性与来源合理性。

### 13.1 BIP 360 原文核验（master 实时抓取）

- 当前 master 的 BIP 360 = **Pay-to-Merkle-Root (P2MR)** v0.12.1（2026-07-24），作者 Beast / Heilman / Foxen Duke，Status: Draft，Requires: 340/341/342，SegWit **version 2**（bc1z 前缀，BIP 173/350 映射），key-path spend 移除。
- 论文引用 [10] 标注（P2MR v0.12.1、commit `e7263a4cfe50`、accessed 28 Sep 2026）与 master 一致，无过时。
- BIP 360 **不指定原生 Winternitz 验证操作码**（论文 §8.1 已正确说明）；Related work 仅讨论 Lamport/WOTS 与 OP_CAT 的未来组合。
- BIP 360 自带测试向量 `bip-0360/ref-impl/common/tests/data/p2mr_construction.json`（version 1，9 个向量）：全部为 secp256k1 `OP_CHECKSIG` 叶脚本的输出构造（leafHash/merkleRoot/scriptPubKey/bip350Address/control blocks），**不含任何 WOTS/哈希签名向量**，且无 key-path spend 场景。

### 13.2 项目数据与 BIP 360 数据集的相关性结论

| 维度 | 项目数据 | BIP 360 数据集 | 相关性 |
|---|---|---|---|
| 核心实验（results_submission/audit_jce/state_*） | 自产，Python 脚本确定性生成 | 无关联 | **不相关**（自足实验） |
| §8 场景引用 | BIP 360 作为未来 PQ 签名宿主场景 | P2MR 草案 | **动机级引用**，非数据依赖 |
| scriptPubKey 结构 | `0x52 0x20 || root` | 同结构 | **结构一致**（项目正确采用） |
| 地址编码 | demo 的 `bc1z` + hex 截断（非 Bech32m，§8.2 已声明） | Bech32m（BIP-350） | **编码不同**，论文精确声明 |
| 叶脚本 | WOTS+（未来 OP_WOTS_VERIFY 假设） | secp256k1 OP_CHECKSIG | **不相关**（BIP 360 无 WOTS 向量） |
| 树承诺 | MSS-LEAF/MSS-NODE（简化模型） | TapLeaf/TapBranch | **不相关**，§8.1 已声明 |
| witness 尺寸 | demo 135 / 4,461 / 66 B | 规范 135 B（depth-1）/ 66 B（P2TR keypath） | **已对齐**（见 13.3） |

### 13.3 本轮修正（合并并行实例产出）

1. **bip360_demo.py witness 口径修正**：secp256k1 叶 witness 133 → **135 B**（补 script/control 的 compact-size 前缀，与 BIP 360 规范 depth-1 witness 1+65+35+34 一致）；WOTS 叶 witness 4,325 → **4,461 B**（134×(1+32)+(1+3)+(1+33)，与论文 §8.3 修正恒等式一致）；P2TR keypath 基线 66 B 不变。`bip360_demo.json` 重生成并断言三方对齐。
2. **论文 §8 同步**：§8.1 补官方向量边界句（p2mr_construction.json 仅覆盖 secp256k1 叶输出构造、无 WOTS、不作符合性证据）；§8.3 的 4,325 改为过去式基线表述，并声明 demo JSON 现存储 4,461 / 135 B。
3. **并行实例并入**（其 round 8 与本次方向一致，已合并去重）：`src/ledger_store.py` 改为**无条件建表**方案（消除空文件判定竞态，比 first-before-journal 更稳，5 循环 + make test 全过）；`tests/test_bip360_vectors.py`（vendored 官方向量 9 个，重算 TapLeaf/TapBranch 根、scriptPubKey、Bech32m 解码、control block，并报告 demo 的符合/不符合关系）；`third_party/bip360/p2mr_construction.json` + README vendored；Makefile test 目标含新测试。
4. **HTML 重渲染** 583,603 B、19 表、13 节；MANIFEST 59 项一致。

### 13.4 数据权威性与来源合理性结论（五条判定）

1. **核心数据自足**：270 事件/5,130 检查/审计 JSON 全部由仓库脚本确定性生成，环境元数据+脚本哈希入账，与 BIP 360 无数据依赖。
2. **引用标注精确**：[10] 标题/版本/commit/访问日期与 master 实时核对一致；§8.1 区分"proposal（非标准）"。
3. **边界声明完整**：bc1z 非 Bech32m、MSS-LEAF 简化、三字节脚本占位、4,461 为理论布局估算（非交易/费用）均逐项列出。
4. **向量使用合规**：BIP 360 官方向量仅用于 envelope 一致性测试（test_bip360_vectors.py），scope 明确不含 PQ 签名；演示的 WOTS 叶明确非 conform 证据。
5. **一致性**：demo JSON 135/4,461/66 与 BIP 360 规范基线与论文 §8.3 三方对齐；make test 全过。

## 14. 数据真实性审计（2026-10-19，用户诉求："数据是否经得住审核，不希望 AI 造数据"）

### 14.1 审计方法（不靠口头保证，全部可复核）
- 新增 `audit/data_authenticity_audit.py`（入口 `make audit-data`，14 项检查全 PASS，输出 `audit/data_authenticity_audit.json` 与本节报告 `reports/DATA_AUTHENTICITY_AUDIT.md`）。
- A. 确定性重跑：audit_jce / state_model / state_persistence / check_counts / robust_stats 5 个脚本重跑，5 个 JSON 哈希与 MANIFEST 全一致 → 审计/统计/状态数据全部脚本确定性生成。
- B. 原始样本真实性：270/270 消息唯一且 64-hex；explicit 269 / compact 267 个不同计时值（非取整常数）；无零计时；离群值 explicit=12、compact=16（>10×median，真实噪声）；字节数 = 公式 + 8B 头部，6 配置全对；环境元数据含 CPU/OpenSSL/clock/loadavg/session/started_utc。
- C. 源码溯源：artifact_hashes 记录的 4 个文件哈希 == 当前工作区文件（可复现）；git 版本化状态如实登记（experiment_jce.py 已提交，experiment_submission.py 与 src 两个文件为未提交工作树版）；旧 3.14.7 样本归档 `results_submission_2026-10-19_py3147.json`。
- D. 生产路径重跑：用相同种子对全部 6 配置调 `run_config()`，每配置 45 行、字节逐项等于权威样本、positive/rejections 全过、first-use 45/45；计时为新值且与权威同量级（w16h4 explicit 中位 0.205 vs 权威 0.260 ms）。
- E. BIP 360 官方向量：vendored 9 向量 version 1，merkleRoot/bip350Address 与上游抽查全 MATCH。

### 14.2 审计中发现并已披露的事实
- 16:15 并行实例按三会话协议重测并替换权威样本（保留会话 s2；旧 3.14.7 样本归档、论文明确禁止新旧计时混用）；论文、robust_stats、MANIFEST 已同步；MANIFEST 70 项与工作树全一致。
- **唯一剩余缺口（作者操作）**：`experiments/experiment_submission.py`、`src/wots.py`、`src/hbs_signature.py` 为未提交工作树版（git HEAD 保留旧版）——记录哈希即工作区哈希，样本按现状可复现，但审稿包应 `git commit` 以版本化。

### 14.3 结论
未发现任何 AI 编造数据迹象；论文每个数字可追溯到保留脚本、权威 JSON 或官方 vendored 向量。逐消息复现已实证：固定种子 `random.Random(20260915)` 硬编码于脚本，重跑 6 配置 270/270 消息/索引/字节/正确性标志与权威样本逐条一致（原"种子未入账"缺口已消除）。
