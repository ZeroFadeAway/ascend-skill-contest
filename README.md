# Ascend Skill Contest

![AGENT SKILL开发大比武](docs/poster.png)

## 比赛题目

本次比赛分为**推理**和**训练**两个赛道。

### 推理赛道

| 题目 | 难度 | 预估时长 |
|------|------|----------|
| [题目1: 推理框架(vllm/sglang/xllm/mindie)部署](inference/question1.md) | ⭐ 初等 | 60 分钟 |
| [题目2: 推理服务化性能摸测](inference/question2.md) | ⭐⭐ 中等 | 90 分钟 |
| [题目3: Torch NPU 算子 API 查询与单算子用例搭建](inference/question3.md) | ⭐⭐ 中等 | 90 分钟 |

### 训练赛道

| 题目 | 难度 | 预估时长 |
|------|------|----------|
| [题目1: 训练框架 Profiling 采集](training/question1.md) | ⭐ 初等 | 60 分钟 |
| [题目2: Verl 部署](training/question2.md) | ⭐⭐ 中等 | 90 分钟 |
| [题目3: 模型迁移（GPU → 昇腾 NPU）](training/question3.md) | ⭐⭐ 中等 | 90 分钟 |

## 参赛流程

1. fork并clone本仓库
2. 根据题目完成对应Skill的编写、自验证
3. 提交PR

## 提交要求

1. 所有题目在同一个PR中提交，完成推理和训练其中一个赛道的题目提交即可。
2. PR模版参考题目要求
3. 目录结构要求：

```
ascend-skill-contest/
├── .agents/             
|    └── skills          # 选手提交的Skill的路径
|           └── skill-name # Skill名称
```

## 评测方式

- 在本项目中运行[opencode](https://opencode.ai)，然后输入题目中的prompt，检查是否完成题目要求。
- 选手编写时所用的AI种类不做限制