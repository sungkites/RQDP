# RQDP 论文代码与数据

对应论文：**面向可信计数查询的多源数据自适应核验方法**。

RQDP（剩余查询动态规划）面向多个共享记录的计数阈值查询，求解最坏核验成本最小的策略。随着查询答案确定，算法按剩余查询重新合并记录类型，并利用反馈支配减少重复计算。

## 数据与隐私

- 资产数据包含 1,163 个对象的谓词抽象。仅保留候选状态、参考状态和实验成本，不含姓名、联系方式、位置文本、原始资产编号或数据库连接信息。
- Flights 数据包含原实验使用的 80 个航班的谓词抽象。
- 数据顺序、候选状态和成本保留原实验设置；原始业务台账不在仓库内。
- 原始实验结果保存在 `results/paper/`，新运行结果写入 `results/runs/`。

## 复现

使用 Python 3.12，无须连接数据库或安装第三方依赖。

```bash
python reproduce.py check
python reproduce.py quality
python reproduce.py primary
python reproduce.py baselines
python reproduce.py scale
python reproduce.py additional
```

六个命令分别对应正确性检查、查询质量、压缩对照、核验策略对照、规模实验和参数实验。计时实验请单独串行运行。

详见 [英文说明](README.md)、[数据说明](DATA_CARD.md)和[实验设置](PROTOCOL.md)。中文摘要见 [abstract_zh.md](paper/abstract_zh.md)。原始台账参考值不等同于独立现场核实结果；实验使用的是同一反馈模型下适配的文献选择规则。
