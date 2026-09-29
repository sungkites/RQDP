# RQDP 论文代码与数据

对应论文：**面向可信计数查询的冲突数据自适应核验方法**（英文题目：*Adaptive Verification for Reliable Count Queries over Conflicting Data*）。

RQDP（剩余查询动态规划）面向多个共享记录的计数阈值查询，求解最坏核验成本最小的策略。查询答案确定后，算法按剩余查询重新合并记录类型，并利用反馈支配减少重复计算。RQDP-A 保持最小最坏成本不变，以未确定查询面积选择能够更早确认答案的并列最优动作。

当前稿件修订调整了题目、文字、引文和期刊排版。算法与实验数值仍对应仓库已发布的代码和数据；V27 之后没有新增实验运行。

## 数据与隐私

- 评价数据包括 Flights、Hospital、Beers 和资产谓词抽象。
- 资产数据只保留候选状态、参考状态和实验成本，不含姓名、联系方式、位置、部门、原始资产编号和数据库连接信息。
- Hospital 和 Beers 采用固定 20% 开发集学习谓词纠正模式，其余记录用于评价。
- 四套数据的谓词输入保存在 `data/`，扩展实验结果保存在 `results/v16/`。

## 扩展实验复现

实验使用 Python 3.12，无须连接数据库。前四项只依赖标准库；生成图片需要 Matplotlib。

```bash
python src/v16_experiments.py check
python src/v16_experiments.py quality --workers 32
python src/v16_experiments.py efficiency --workers 32
python src/v16_structured.py 32
python src/v16_figures.py
```

图片及对应的绘图数据写入 `artifacts/figures/`。计时结果与硬件有关，仓库中的 `results/v16/` 是论文使用的归档结果。

规模 8 时，RQDP 相对逐记录动态规划加速 4.06—45.09 倍。RQDP-A 在四个数据集上的 F1—成本面积均不低于 RQDP，并在 Beers 上取得最高值。受控任务进一步用于说明：只有当查询推进后出现新的剩余等价类型时，动态压缩才会明显优于静态分组。

详见 [英文说明](README.md)、[数据说明](DATA_CARD.md)和[实验设置](PROTOCOL.md)。原始业务台账不在仓库内，资产参考值也不等同于独立现场核实结果。文献方法是在统一状态、反馈和停止条件下实现的选择规则，不代表原作者完整系统的直接运行结果。
