# JCE 投稿就绪清单（2026-10-19）

本清单跟踪投稿主稿 `paper/paper_jce.md`/`.html` 距离可投稿的状态。分「已就绪」「待作者提供/操作」「技术债」三类。

## ✅ 已就绪（内容与格式）

- [x] **路线 A 定位**：工程审计 / 可复现评估；不宣称新 primitive、不分配密码学安全级别（Abstract、§2.2、§7.1）
- [x] **术语区分**：自研算法称 “Winternitz prototype”（固定前缀 SHA-256、checksum 有缺陷），“WOTS+” 仅指标准方案（§2.2）
- [x] **对比边界**：明确不宣称优于 XMSS/LMS/SLH-DSA（§2.1、§2.4）
- [x] **实验强度**：270 个新消息样本 + 原始观测 + 均值/样本标准差（§6.4）
- [x] **同机标准参考**：SLH-DSA-128s/128f C `-O3` 同机实测（§6.7 Table 11）；§6.8 新增 PQClean ML-DSA/SLH-DSA + C 版原型的同条件三 session 基准（Table 11a）— **2026-10-19 新增**
- [x] **FIPS 引用正确**：204 = ML-DSA（Module-Lattice-Based）、205 = SLH-DSA（Stateless Hash-Based）
- [x] **BIP-0360 核验**：draft v0.12.1、访问 2026-09-28、作者齐全（§8、[10]）
- [x] **DA / provenance / AI 披露**（§9.2）
- [x] **摘要 247 词**（JCE 要求 150–250）、**关键词 6 个**（要求 4–6）
- [x] **复现入口**：路径已校正为子目录形式，并含同机基准命令（§9.1）
- [x] **md → html 已同步重渲染**（`charts/render_jce.py --from-markdown`，图片 base64 内嵌、离线可看）

## ⏳ 待作者提供 / 操作（助手无法代做）

1. **作者与声明信息**：姓名、单位、通讯邮箱、作者贡献、资助、利益冲突（JCE 强制要求；未擅自填写）。
2. **归档 DOI**：GitHub 公开本仓库 → Zenodo 关联该仓库 → 打 tag `v1.0` + Release 得概念 DOI → 回填到 §9.2 与 `CITATION.cff`。
3. **期刊选择**：先确定“0 版面费”定义（订阅制免 APC / 钻石 OA / 订阅+green OA 组合），再据定义给候选短名单。
4. **投稿源文件**：JCE 要求可编辑源（LaTeX 或 Word）+ PDF；当前为 md/html，需按 Springer 期刊模板转 LaTeX。
5. **刊物核实**：目标刊的 APC / 索引（Scopus、SCIE）/ 审稿周期 / 是否正规——投稿前逐一实时核实（助手不编造此类数据）。

## ⚠️ 技术债（不影响现有图，重生成前需修）

- `charts/make_charts_jce.py` 仍按旧结构读取 `audit_jce.json`（顶层 `['rows']`、旧字段 `explicit_pk_payload_bytes`/`sign_steps`），而 `audit/audit_jce.py` 现产出嵌套结构（`byte_accounting.rows`/`table4_exact_chain_work.rows`，字段 `explicit_key_payload_bytes`/`sign_chain_calls`）。重生成 `fig_jce_*` 前需适配其数据读取逻辑；改动涉及图表数值语义，建议作者确认后再改。现有 `figures/fig_jce_*` 产物可先行使用。

## 建议的投稿动作顺序

1. 补作者与声明信息 → 2. GitHub + Zenodo 得 DOI 并回填 → 3. 定“0 版面费”定义并选刊 → 4. 按 Springer 模板转 LaTeX 源文件 → 5. 核对 APC/索引/合法性 → 6. 投递。

## 本轮审稿修订（2026-10-19，已执行）

对照外部审稿意见（结论：大修）完成的修订，详见 `reports/REVIEW_GAP_ANALYSIS.md`：

- [x] **表 8 / 表 9 / §6.4 运行环境与保留工件对齐**：表 8 按 `results_submission.json` 更新（CPython 3.14.7 / macOS 15.7.7 / arm64）；表 9 按重新生成的 `path_traversal.json` 更新；删除未归档运行残留值（0.932…、CPython 3.7.3 / x86_64）
- [x] **§7.5 状态模型数字修正**：52 状态 / 351 转移 → 73 状态 / 355 转移（与 `state_model_jce.json` 及重跑一致）
- [x] **§6.4 计数口径**：18 棵独立树 / 270 签名事件 / 540 验证观测（每模式 270）
- [x] **表 8a 字段级序列化拆分表**：6 配置 ×（链元素 / 认证路径 / 头部 / 合计）
- [x] **§7.1 显式安全目标声明**：不主张任何密码学安全性质
- [x] **§7.4 durable-before-release 时序约束**：Reserve 必须先于 Emit 持久化提交
- [x] **§6.5 的 5,130 检查分解精确化**：270 记录中 180 次真实重复索引拒绝、90 次首次使用
- [x] **Figure 3 重新生成并同步**：figure3.png/svg == fig_submission.png；HTML 已重渲染（`render_jce.py --from-markdown`）
- [x] **ARTIFACT_MANIFEST.txt 更新**：子目录相对路径 + 重算 SHA-256（20 项）
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）

## 第二轮审稿修订（2026-10-19，已执行）

- [x] **5,130 检查口径自动复现**：新增 `experiments/check_counts.py` → `check_counts.json`，论文附录 B 表 13（270/270/4,320/90/180/5,130）；§6.5 说明 used-index 按配置新建、跨 3 树累积（树 0 首用、树 1/2 重复）
- [x] **高方差计时稳健统计**：新增 `experiments/robust_stats.py` → `robust_stats.json`，论文表 8b（中位数/IQR/配对 Δ/显式更慢占比）；正文明确"尺寸节省为明确结果、时间差异为探索性观察"，全部样本保留、无异常点删除
- [x] **三层证据框架**：§2.2 新增算术审计/功能测试/密码学分析分层；全文措辞审计（统一 repaired variant，无标准符合性误导）
- [x] **SLH-DSA 基准定位**：表 7 题注补"非 Pareto 优势或安全等价证据"
- [x] **状态恢复故障场景表**：§7.4 表 12（5 类故障 × 处理/不复用保持/代价）
- [x] **细节修订**：§5.1 编码字节数边界注明；§6.5 特定实现消融定位；§8.1 illustrative 定位；§9.1 复现命令补两脚本
- [x] **文献核验**：[7] Shielded Bitcoin 可访问、补访问日期；[10] BIP 360 钉 master 提交哈希 `e7263a4cfe50`（2026-08-03）
- [x] **HTML 重渲染**：380,979 B、13 节、15 表、校验通过；MANIFEST 更新为 25 项
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）

## 第三轮审稿修订（2026-10-19，已执行）

- [x] **P0 密钥身份修复**：`experiment_submission.py` 的 used-index 改为 (tree, index) 键；重跑实验（270 首用 / 0 误判）；表 9/9b/图 3/表 14/§6.5 全部同步新数值
- [x] **P0 审计状态测试**：`audit_jce.py` 新增 5 项 key-identity 场景（同树同索引重复拒绝、同树异索引允许、异树同索引允许、崩溃重启重放拒绝），全部符合预期
- [x] **检查次数 vs 独立案例**：§6.5/附录 B 明确 5,130 为断言数，独立案例=270 事件+16 拒绝类型+审计确定性检查
- [x] **统计独立性**：§6.4 树级分组（3 树为分组单位）；配对差值/中位数/IQR 保留；无显著性检验声明保留
- [x] **checksum 测试**：§4.2 修复编码一致性（每 w 数字/链调用/长度一致性由 audit 检查）；无外部独立向量如实声明
- [x] **载荷公式与参数绑定**：表 4 数字复核一致；§5.1 参数/索引/签名/根提供方与信任来源句
- [x] **相关工作差异表**：新增表 1；表号全局重排（1→2 … 13→14、8a/8b→9a/9b）并校验
- [x] **§8 假设清单**：witness 项数、长度前缀、脚本占位、地址前缀、承诺方式逐项列出
- [x] **重渲染与清单**：HTML 390,373 B、16 表、校验通过；MANIFEST 25 项重算
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）

## 第四轮审稿修订（2026-10-19，已执行）

- [x] **安全边界贯穿**：§2.2 "repaired=编码缺陷修复非安全修复"显式定义；§7.1 新增攻击面/未证明性质/适用边界五条清单
- [x] **270/540/5,130 复核**：§6.4 四统计单位显式清单；12 项第 3 轮回归检查全过
- [x] **状态恢复三层证据**：§7.4 抽象模型/实现/系统三层框架；audit 新增 state_boundary_tests（并发分配交错、快照恢复、旧备份回滚，全部确定性通过）
- [x] **表 8 非等安全等级标注** + 四类数量不可互换说明
- [x] **§2 工程评估定位句**；§5 尺寸口径统一注记；§8 成分归属与根承诺绑定；参考文献访问日期统一
- [x] **重渲染与清单**：HTML 395,478 B、16 表、校验通过；MANIFEST 25 项重算
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）
- [ ] **系统级状态验证**（真实存储引擎/并发/回滚）：列入 §9.3，投稿前可选补强

## 第五轮审稿修订（2026-10-19，已执行）

- [x] **假设—实现—测试对应表（表 12a）**：S1/S2/S3/S5 四行，逐项给出所需证据与本文状态（未提供/模型级）
- [x] **命题 2 结论精确化**：新增 Precise statement（仅凭种子+确认链无法精确重建暴露集；需额外持久化暴露状态或停用根；非笼统"不可恢复"主张）
- [x] **表 4 派生减少比例列**：49.3%/48.6%/47.2%，限定为所定义编码内计算，非协议级/安全等价
- [x] **16 表题注来源标记**：[Derived]/[Measured]/[Illustrative]/[Model] 等；表 7 补"原样本未保留"句
- [x] **§8 标题统一示意模型**；摘要精简（合并技术清单，保留研究问题/结果/边界）
- [x] **渲染脚本修复**：from_markdown 同步更新 nav，消除旧 TOC 锚点残留
- [x] **验证与交付**：33 项检查全过；HTML 398,592 B、17 表；MANIFEST 25 项重算
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）
- [ ] **系统级状态验证**（真实存储引擎/并发/回滚）：表 12a 各行"未提供"，列入 §9.3

## 第六轮同步（2026-10-19，已执行）：原生 C 基准 + durable-state

- [x] **§6.8 同条件原生 C 基准**：PQClean ML-DSA-44/65、SLH-DSA-128s/128f + C 版 repaired prototype；clang 17 `-O3`；同一 Apple M1；3 个独立 session（rotated order、12 s cooldown）；101/31 次重复；跨 session 中位数 [min–max]；Table 11a + Figure 4
- [x] **§7.6 durable-state 故障注入**：append-only 哈希链日志、原子 head、独立高水位、`flock`；6/6 测试（复用拒绝、reserve 后崩溃烧叶、部分回滚检测、8 进程并发唯一、篡改检测、容量上限）；Table 14；明确残余风险（全部本地状态回滚需可信单调锚点）
- [x] **§4.3 h=7 实例**：WOTS+ recovered = 2,368 B（含 8 B header 为 2,376 B）；raw Lamport 不可恢复端点（叶承诺完整 OTS 公钥）
- [x] **§6.2 / §7.1 / §7.4 / §9.3 / §10 同步**：删除"无 Python-to-C speed-up"旧口径；表 12a 的 S1/S2/S3 状态升级为"最小 durable allocator 已测试，生产存储引擎仍缺"；结论加入原生基准与状态测试
- [x] **新增文献 [11] PQClean**；摘要新增 3 句、247 词（JCE 150–250）
- [x] **HTML 重渲染**：558,543 B、19 表、4 图、内部链接校验通过
- [x] **MANIFEST 更新**：44 项，新增 `bench/native/*`、`state_demo/*`、`experiments/native_results*.json`、`figures/fig_native_benchmark.png`、`src/ledger_store.py`、`audit/state_persistence_tests.*`
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：仍为作者操作（投稿前必须）
- [ ] **生产级存储引擎 / 真实多进程协调**：§7.6 仍为最小 demo，列入 §9.3

## 第六轮补强（2026-10-19，已执行）：SQLite 事务后端（表 12a 数据库事务证明路线）

- [x] **`src/ledger_store.py`**：SQLite 持久化账本（BEGIN IMMEDIATE + UNIQUE(tree_id, leaf_index) + epoch 单调持久化 + 外部 checkpoint）
- [x] **`audit/state_persistence_tests.py` + `.json`**：三类确定性系统级测试全过（all_as_expected=True）——并发事务（8 进程 96 请求 + 16 线程 192 请求，唯一且无丢失）、崩溃注入（COMMIT 前回滚可重预留 / COMMIT 后持久拒绝重用）、回滚检测（一致快照继续 / 旧备份 epoch 回退→停用根不重发）
- [x] **论文同步**：表 12a 的 S1/S2/S3 状态列升级（文件锁 allocator + SQLite 事务后端）；§7.6 新增 Database-transaction route 段；§7.1 / §7.4 三层证据 / §9.1 命令 / §9.2 工件 / §9.3 第 3 项 / 结论同步
- [x] **边界披露**：SQLite 覆盖进程崩溃级安全；断电、多主机、硬件故障不在范围（§9.3 与测试 note 一致）；S5 仍为威胁模型
- [x] **验证与交付**：HTML 校验通过（558,166 B、19 表）；MANIFEST 41→44 项
- [ ] **S5 无密钥克隆**：仅威胁模型陈述，无代码级预防（如实披露）


## 第七轮同步（2026-10-19，已执行）：执行方案落地 + checksum 边界测试 + make 复现入口

- [x] **基线冻结**：git tag `review-baseline-r7`（HEAD c54d85a6）；19 关键文件 SHA-256 入账
- [x] **复现验证**：6 个确定性脚本重跑全过，5 个 JSON 哈希与基线一致（audit / state_model / state_persistence / check_counts / robust_stats）；计时实验保留第 3 轮权威样本未重跑
- [x] **checksum 边界测试（方案 3.3）**：`audit_jce.py` 新增双独立 oracle（divmod 整数路径 + 序列化位串路径）vs 生产移位编码；w∈{4,16,256} 各 9 边界 case（全零/最小/单 bit 低中高位/最大/进位邻接/随机），27/27 对拍 + 范围 + 位数 + 总长度不变量全过；§4.2 同步
- [x] **make 复现入口（方案 9.2）**：Makefile `test`（确定性审计数秒）/ `reproduce-quick` / `reproduce-full`（含计时重跑警告）
- [x] **竞态修复**：SQLite 首次打开竞态（journal_mode 写文件破坏空文件判定 → no such table）修复；5 次循环 + make test 全过
- [x] **HTML 重渲染**：559,147 B、19 表、13 节、校验通过；MANIFEST 45 项
- [ ] **独立树扩展（4.2）**：3→20-30 棵，需决策（会替换计时权威数据）
- [ ] **计时分项（4.4）/ 图 A/B/C + bootstrap（7.3）/ F1-F7 故障点（5.4）/ 配置外置（9.3）**：决策项
- [ ] **公开仓库 + Zenodo DOI + tag v1.0**：作者操作（投稿硬门槛）

## 第八轮（2026-10-19，已执行）：代码与数据审计，重做同条件基准

本轮先验证实现再改表：所有改动均由代码证据触发，详见 `reports/CODE_AUDIT.md`。

- [x] **A1 校验和修复落到 `src/wots.py`**：新增 `wots_checksum()`（`c_j = floor(C / w^(L2-1-j)) mod w`），sign/verify 共用；旧编码对任意消息恒返回 `[0,0,0]`，已实测复现；边界 c∈{0,1,15,16,959,960} + 校验和链前进一步拒绝
- [x] **A2 C 原型改为逐字节同构造**：`SUB-SK` / `SUB-LEAF` / `UMT-LEAF`(0x01) / `UMT-NODE`、确定性派生、同树布局与序列化；`--root h` 与 Python `build_tree` 在 h=1/2/4/7/8 根与叶完全一致
- [x] **A3 compact 验证重复链计算修复**：原 `wots_rebuild_pk` + `wots_verify` 两遍；修复后 0.246→0.133 ms，与 explicit 0.131 ms 一致
- [x] **A4 签名循环重建树修复**：改为从预计算层读路径，与 Python `auth_path` 同边界
- [x] **A5 计时边界统一**：同 64 B 消息、同序列化输入、同操作顺序；Python 解析开销单列
- [x] **A6 撤回混用两个代码库的 “1.5–1.7×”**：改为逐操作 **1.73 / 1.82 / 1.93 / 1.81×**（h=8，配对三会话）；Table 11a 全部替换
- [x] **A7/A8 计数与字节守恒**：`tests/test_chain_counts.py`（510+495=1005=67×15）、`tests/test_serialization.py`（6 配置长度恒等式，最小 1,224 B）
- [x] **A9 状态测试有效性**：崩溃注入改为“事务仍打开时进程死亡”（不再先显式 rollback）；SQLite 首次打开建表竞态修复；8 进程 + 16 线程零重复/零丢失
- [x] **KAT 重生成**：`kat_wots.json` 由修复后实现生成，`roundtrip_ok=true`；附录 A 公钥前缀不变
- [x] **复现入口**：`make test` 增加三个测试；§9.1 命令补 `tests/*` 与 `bench_like_for_like.py`；新增 `charts/make_native_figure.py`
- [x] **HTML 重渲染**：582,057 B、19 表、4 图、内部链接校验通过
- [ ] **S5 无密钥克隆**：仍为威胁模型陈述（未变）
- [ ] **公开仓库 + Zenodo DOI**：作者操作（未变）

## 第九轮（2026-10-19）：BIP-0360 相关性核查与向量锚定

- [x] **相关性结论**：项目未使用 BIP-0360 的任何数据集（`p2mr_construction.json`、Python ref-impl 均未接入）；签名/验证/性能数据与本仓库 HBS 构造相关，与 BIP 无关；BIP 仅提供 §8 的外壳与动机。
- [x] **向量锚定**：`third_party/bip360/` 纳入 9 条官方向量（7 正 2 负）+ 来源说明（BIP v0.12.1 / `e7263a4cfe50`；向量文件 `3e3e4347e277`；SHA-256 `cd02da0b…`）。
- [x] **新增测试**：`tests/test_bip360_vectors.py` 重算 TapLeaf/TapBranch 根、校验 `5220||root`、Bech32m v2 地址、`1+32m` 控制块路径；7 正 2 负全过；明确声明只验证信封，不验证签名方案。
- [x] **修正数字不一致**：demo JSON 原为 4,460（并行修改 off-by-one），代码复算 4,461；已重生成。论文 §8.3 区分 4,325（无前缀）/ 4,461（134 项前缀，已存）/ 135 B（BIP 自身 depth-1 示例）。
- [x] **论文同步**：§8.1 说明向量覆盖范围；§8.3 修正假设清单；§9.1 增加测试命令；§9.2 列入向量与测试；HTML 重渲染 583,603 B。
- [ ] **地址仍是示意字符串**：`p2mr_address()` 未实现 Bech32m（论文 §8.2 已披露）；若要写成真实地址需引入 BIP-350 编码器。


## 第八轮同步（2026-10-19）：BIP 360 数据集相关性核查

- [x] **BIP 360 原文核验**：master = P2MR v0.12.1（SegWit v2/bc1z、key-path 移除、不指定 WOTS opcode）；论文 [10] 标注一致
- [x] **数据集相关性判定**：核心实验自足无关；§8 为动机级引用；demo 结构与规范对齐、编码/叶脚本/树承诺差异均已声明
- [x] **bip360_demo witness 口径修正**：secp 叶 133→**135 B**（规范一致）；WOTS 叶 4,325→**4,461 B**（论文 §8.3 一致）；P2TR 基线 66 B；JSON 断言三方对齐
- [x] **论文同步**：§8.1 官方向量边界句；§8.3 过去式基线 + demo 对齐声明
- [x] **并行实例合并**：ledger 无条件建表（竞态修复升级）、test_bip360_vectors.py（vendored 9 官方向量）、third_party/bip360/、Makefile 含新测试；make test 全过
- [x] **HTML 重渲染 + MANIFEST 59 项一致**
- [ ] 公开仓库 + Zenodo DOI + tag v1.0（作者操作，未变）

## 第十轮（2026-10-19）：计时样本重测 + 环境可核验 + 数字自动对账

- [x] **重测原因**：原样本记录 CPython 3.14.7（真实版本但本机未安装），3.14.3 重跑中位数慢 1.12–1.19×（单次最高 2.05×），绝对毫秒不可按记录环境复现。
- [x] **环境元数据**：`experiment_submission.py` 现记录检测到的 CPU 型号、完整 Python 版本、OpenSSL、逻辑核数、`perf_counter` 实现与分辨率、1/5/15 分钟负载、会话标签、UTC 起始时间；不再硬编码 CPU 字符串。
- [x] **三会话与固定选择规则**：`run_submission_sessions.py` 跑 3 个独立会话，保留“六个配置验证中位数的中位数”为总体中位的那一场（并列取小号）；跨会话每配置中位数离散度 5–17%，保留 s2。
- [x] **旧样本归档**：`experiments/results_submission_2026-10-19_py3147.json`，不与新表混用。
- [x] **自动对账**：`sync_paper_tables.py` 从 JSON 渲染 Table 9/9b 与稳健统计段；`tests/test_paper_numbers.py` 解析论文表格，逐格比对 Table 9/9b/11a 与全局计数，任一不符即失败。
- [x] **论文同步**：Table 9、Table 9b、稳健统计段、Runtime 段（含负载与跨会话离散度）、§9.1/§9.2 更新；HTML 重渲染 584,714 B。
- [x] **测试**：`make test` 全过（含 BIP 向量、论文数字对账）。
- [ ] **主机仍未绑定**：新样本在 loadavg 8.5/10.1/11.5 下测得，绝对值偏保守；空闲机器复跑会更快，已披露。

## 数据真实性审计（2026-10-19，已执行）：`make audit-data` 14 项检查全过
- [x] **确定性重跑**：5 个脚本重跑，5 个 JSON 哈希与 MANIFEST 全一致（audit/state_model/state_persistence/check_counts/robust_stats）。
- [x] **原始样本真实性**：270/270 消息唯一、64-hex；计时 269/267 个不同值、无零值、离群值 12/16；字节 = 公式+8B 头部全 6 配置对；环境元数据含 CPU/OpenSSL/clock/loadavg/session。
- [x] **生产路径重跑**：6 配置 × 45 行，字节逐项等于权威、检查全过、首用 45/45；计时同量级。
- [x] **源码溯源**：artifact_hashes == 当前工作区文件；git 版本化状态已登记；旧 3.14.7 样本归档。
- [x] **官方向量**：vendored BIP 360 与上游 merkleRoot/bip350Address 抽查全 MATCH。
- [x] **报告与入口**：`reports/DATA_AUTHENTICITY_AUDIT.md`、`audit/data_authenticity_audit.json`、Makefile `audit-data` 目标、MANIFEST 70 项一致。
- [x] **逐消息复现实证**：固定种子 `random.Random(20260915)`（脚本内硬编码）重跑 6 配置，270/270 消息/索引/字节/正确性标志与权威样本逐条一致。
- [ ] **作者操作（唯一缺口）**：`experiments/experiment_submission.py`、`src/wots.py`、`src/hbs_signature.py` 未提交 → `git commit` 版本化后随审稿包提交。

## 第十一轮（2026-10-19）：按修改方案补齐三处硬缺口

- [x] **环境描述矛盾修正**：§6.8 原写 “macOS 14, build 24G720”，实机为 **macOS 15.7.7 / 24G720**，已改；§6.7 的 CPython 3.14.7 与 §6.4 的 3.14.3 明确为两次不同运行并说明不得合并。
- [x] **状态故障证据表（Table 15）**：ST-01–ST-10，逐行给出注入点、预期、实测与证据文件；ST-10（数据库与检查点同时回滚）明确标为“不可检测边界”，不是通过项。
- [x] **树级敏感性**：稳健统计段新增“同一配置三棵树的显式中位数跨度为 3.3–15.1%”，说明树身份不解释配置间差异，配对差在事件内计算。
- [x] **对账范围扩展**：`tests/test_paper_numbers.py` 现覆盖 Table 9、9b、10、11a、14、15 与 270/5,130 计数；`render_jce.py` 表格数断言 19→20。
- [x] **HTML 重渲染**：589,487 B、20 表、校验通过；`make test` 全过。
- [ ] **BIP 360 正文压缩/附录化**：方案 P2 项，尚未执行（当前 §8 已明确为示意核算）。
- [ ] **公开仓库 + DOI + 版本标签**：作者操作，仍未完成。
