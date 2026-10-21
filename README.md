# HBS-PQ：基于哈希的后量子签名研究原型

从零实现的 **Lamport OTS / WOTS+ + Merkle 树**研究原型（fixed-prefix 构造）。论文将其定位为实现审计、载荷核算与状态管理的可复现工程研究；**不声称与 NIST FIPS 204（ML-DSA）、FIPS 205（SLH-DSA）的安全等价**，标准方案尺寸仅作为 published size context 引用。研究动机为 **BIP-0360（Pay-to-Merkle-Root）** 所预留的后量子签名脚本路径。



---

## 目录结构

| 目录 | 内容 |
|---|---|
| `src/` | 核心密码学实现：`hbs_signature.py`（Lamport OTS + Merkle 树）、`wots.py`（WOTS+）、`wots_bench.c`（C 基准） |
| `experiments/` | 实验脚本（`experiment_jce.py`、`experiment_submission.py`、`make_kat.py`、`bip360_demo.py`、`run_sphincs_benchmark.py`）与实测数据（`results*.json`、`kat_wots.json`、`bip360_demo.json`、`kat_128s.rsp`） |
| `bench/native/` | 同条件原生 C 基准：PQClean ML-DSA/SLH-DSA + C 版 repaired prototype（`build.sh`、`run_sessions.py`、`bench_proto.c`、`bench_std.c`） |
| `state_demo/` | durable-state 分配器（哈希链日志、原子 head、高水位、`flock`）与 6 项故障注入测试（`test_state.py`） |
| `charts/` | 图表与渲染脚本：`make_charts_jce.py`、`make_submission_figure.py`、`make_native_figure.py`、`render_jce.py` |
| `figures/` | 图表产物（`fig_jce_*`、`fig_submission.*`、`figure3.*`、`fig_native_benchmark.png`） |
| `tests/` | 编码边界（E1–E8）、链调用计数、序列化长度恒等式的独立测试 |
| `paper/` | 论文文稿：`paper_jce.md/html`（投稿主稿）及预览图 |
| `audit/` | 原型审计（`audit_jce.py/json`）、抽象状态模型（`state_model_jce.py/json`）与 SQLite 状态测试（`state_persistence_tests.py/json`） |
| `reports/` | 研究报告（`RESEARCH_REPORT.md`）、投稿评估与代码审计（`CODE_AUDIT.md`） |
| `third_party/` | 第三方参考源码（`bip360/`，BIP 360 官方 P2MR 向量，vendored 供 `tests/test_bip360_vectors.py` 校验） |
| `evidence/` | 投稿就绪验收日志（`t01–t12`、`a06–a12`，对应 `submission_readiness.csv` 的证据文件） |
| `LICENSE` | MIT 许可 |

## 数据流

```
experiments/experiment_*.py  →  experiments/results*.json
        ↘  make_kat.py → experiments/kat_wots.json → audit/audit_jce.py → audit/audit_jce.json

charts/make_charts_jce.py  ──读 experiments/*.json + audit/audit_jce.json──→  figures/fig_jce_*.png
charts/make_submission_figure.py ──读 experiments/results_submission.json──→ figures/figure3.*

paper/paper_jce.md（引用 ../figures/fig*.png）──render_jce──→ paper/paper_jce.html（图片 base64 内嵌，离线可看）
```

## 快速开始

所有脚本基于自身位置定位项目根（`Path(__file__).resolve().parents[1]`），**从任意目录调用均可**，无需先 `cd`。

```bash
# 一键复现入口（推荐）：测试 + 数据真实性审计
make test          # 11 步：5 测试 + 3 审计 + 状态 + 计数 + 稳健统计 + 渲染
make audit-data    # 数据真实性审计（14 项检查，确定性输出）

# 核心自检（纯标准库，无需第三方依赖）
python3 src/wots.py                 # WOTS+ 自检
python3 src/hbs_signature.py        # Lamport + Merkle 自检

# KAT 向量 / 审计 / 状态模型（纯标准库）
python3 experiments/make_kat.py     # 生成 experiments/kat_wots.json
python3 audit/audit_jce.py          # 复现审计 → audit/audit_jce.json
python3 audit/state_model_jce.py    # 73 状态 / 355 转移模型检查 → audit/state_model_jce.json
python3 state_demo/test_state.py    # 6 项故障注入测试
python3 audit/state_persistence_tests.py  # SQLite 事务/并发/回滚测试

# 基准实验（会覆盖对应 results*.json；计时含随机性）
python3 experiments/experiment_submission.py  # 投稿版配对实验（较慢）
python3 bench/native/build.sh                 # 原生 C 基准（需网络克隆 PQClean）

# 图表（需 matplotlib + numpy）
python3 charts/make_submission_figure.py

# 论文渲染（render_jce 需 mistune）
python3 charts/render_jce.py        # paper/paper_jce.md → paper/paper_jce.html
```

## 依赖

| 脚本 | 依赖 |
|---|---|
| `src/*`、`experiments/*`、`audit/*` | 仅 Python 3 标准库 |
| `experiments/run_sphincs_benchmark.py` | C99 编译器（`cc`/`gcc`），自动编译 `third_party/sphincsplus-ref` |
| `charts/make_charts_jce.py`、`charts/make_submission_figure.py` | `matplotlib`、`numpy` |
| `charts/render_jce.py` | `mistune` |

## 注意事项 / 已知事项

1. **投稿图 3 的两套命名。** 磁盘产物为 `figures/fig_submission.png/.pdf/.eps`；`charts/make_submission_figure.py` 当前输出为 `figures/figure3.png/.svg` + `figures/path_traversal.json`，二者指向同一张论文 Figure 3。
2. **实验脚本会覆盖 `results*.json`。** 计时类数据含运行随机性，重跑会使数值变化；KAT/audit/state_model 为确定性输出（固定种子），重跑结果稳定。权威样本与三会话记录见 `experiments/results_submission.json` 与 `experiments/results_submission_sessions.json`。
3. **`archive/`**（历史备份）与 **`merkle_wots_experiment_starter/`**（外部审查模板的合成示例代码包，自认非真实算法）仅本地保留，不参与公开仓库与任何验证流程。
4. **`ARTIFACT_MANIFEST.txt`** 是 SHA-256 工件清单（当前 88 项），记录论文引用的全部代码/数据/测试/报告；`make test` 会校验其与工作树一致。
5. **`experiments/kat_128s.rsp`** 内容为 `404: Not Found`（下载失败残留），已在论文 §4.2 披露且未被任何验证流程引用；真正的本地回归向量为 `experiments/kat_wots.json`。
6. 原型为教学/研究级，未做域分离与常数时间硬化，**不可直接用于生产**；论文未分配任何密码学安全等级（详见 `paper/paper_jce.md` §2.2/§7.1/§10 与 `reports/RESEARCH_REPORT.md`）。

## 引用与许可

- 引用本工件请使用 `CITATION.cff`（投稿前需补全作者姓名与单位）。
- 代码与文档以 **MIT 许可** 发布（见 `LICENSE`）；论文中引用的第三方标准（RFC/NIST/BIP/PQClean）版权归其各自所有者。
