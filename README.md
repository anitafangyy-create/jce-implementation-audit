# HBS-PQ：基于哈希的后量子签名研究原型

从零实现的 **Lamport OTS / WOTS+ + Merkle 树**研究原型（fixed-prefix 构造）。论文将其定位为实现审计、载荷核算与状态管理的可复现工程研究；**不声称与 NIST FIPS 204（ML-DSA）、FIPS 205（SLH-DSA）的安全等价**，标准方案尺寸仅作为 published size context 引用。研究动机为 **BIP-0360（Pay-to-Merkle-Root）** 所预留的后量子签名脚本路径。

投稿主稿：`paper/paper_jce.html`（Journal of Cryptographic Engineering 修订稿）。中文过程报告见 `reports/`。早期方案论文（已弃用方向）与 NIST 基准工具已拆分为独立仓库：`../hash-based-signature-proposal/`、`../nist-pqc-benchmarks/`。

---

## 目录结构

| 目录 | 内容 |
|---|---|
| `src/` | 核心密码学实现：`hbs_signature.py`（Lamport OTS + Merkle 树）、`wots.py`（WOTS+）、`wots_bench.c`（C 基准） |
| `experiments/` | 实验脚本（`experiment_jce.py`、`experiment_submission.py`、`make_kat.py`、`bip360_demo.py`、`run_sphincs_benchmark.py`）与实测数据（`results*.json`、`kat_wots.json`、`bip360_demo.json`、`kat_128s.rsp`） |
| `charts/` | 图表与渲染脚本：`make_charts_jce.py`、`make_submission_figure.py`、`render_jce.py` |
| `figures/` | 图表产物（`fig_jce_*`、`fig_submission.*`、`figure3.*`） |
| `paper/` | 论文文稿：`paper_jce.md/html`（投稿主稿）及预览图 |
| `audit/` | 原型审计（`audit_jce.py/json`）与抽象状态模型（`state_model_jce.py/json`） |
| `reports/` | 中文研究报告（`RESEARCH_REPORT.md`）与投稿评估（`SUBMISSION_REVIEW.md`） |
| `third_party/` | 第三方参考源码（`sphincsplus-ref/`，SPHINCS+ 官方实现，供 `src/sphincs_vectors.py` 校验 KAT 用） |
| `archive/` | 历史备份（`备份1/`、`revision_backup/`），不参与运行，仅供追溯 |

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
# 核心自检（纯标准库，无需第三方依赖）
python3 src/wots.py                 # WOTS+ 自检
python3 src/hbs_signature.py        # Lamport + Merkle 自检

# KAT 向量 / 审计 / 状态模型（纯标准库）
python3 experiments/make_kat.py     # 生成 experiments/kat_wots.json
python3 audit/audit_jce.py          # 复现审计 → audit/audit_jce.json
python3 audit/state_model_jce.py    # 73 状态 / 355 转移模型检查 → audit/state_model_jce.json

# 基准实验（会覆盖对应 results*.json；计时含随机性）
python3 experiments/experiment_submission.py  # 投稿版配对实验（较慢）
python3 experiments/run_sphincs_benchmark.py  # SPHINCS+ 同机基准（内部编译 third_party/sphincsplus-ref，Table 7）

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

1. **`make_charts_jce.py` 与新版 `audit_jce.json` 结构不匹配（整理前已存在，非本次整理引入）。** 当前 `audit/audit_jce.py` 重写后产出嵌套结构（数据在 `byte_accounting.rows` / `table4_exact_chain_work.rows`，字段为 `explicit_key_payload_bytes` / `sign_chain_calls` 等），而 `charts/make_charts_jce.py` 仍按旧结构读取顶层 `['rows']` 及旧字段名（`explicit_pk_payload_bytes` / `sign_steps`）。运行前需先同步其数据读取逻辑；`figures/fig_jce_*.png` 现有产物不受影响。
2. **投稿图 3 的两套命名。** 磁盘产物为 `figures/fig_submission.png/.pdf/.eps`；`charts/make_submission_figure.py` 当前输出为 `figures/figure3.png/.svg` + `figures/path_traversal.json`，二者指向同一张论文 Figure 3。
3. **实验脚本会覆盖 `results*.json`。** 计时类数据含运行随机性，重跑会使数值变化；KAT/audit/state_model 为确定性输出（固定种子），重跑结果稳定。
4. **SPHINCS+ KAT/交叉验证工具**（`sphincs_vectors.py`、`sphincs_crosscheck.py`、`mlkem_bench.py` 等）已随拆分移入独立仓库 `../nist-pqc-benchmarks/`。
5. **`archive/`** 内为历史版本备份（含早期论文、旧实验与第三方源码快照），仅作追溯，不影响上述任何流程。
6. **`ARTIFACT_MANIFEST.txt`** 是一份 SHA-256 工件清单，但其文件名为**扁平形式**（如 `audit_jce.py`、`results_jce.json`），是目录整理前生成的；整理后同名文件已位于 `audit/`、`experiments/` 等子目录中，核对时请按新路径折算。清单中提到的 `paper_jce_v2.html` 当前不在工作树内。
7. 原型为教学/研究级，未做域分离与常数时间硬化，**不可直接用于生产**（详见 `reports/RESEARCH_REPORT.md` 第 6 节与 `paper` 安全分析章节）。